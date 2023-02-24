class Spoke {
  constructor(group) {
    this.index = -1;
    this.group = group;
    this.registrations = 0;
    this.registrationMap = null;
    this.initiatorRandoms = [];
    this.aggregationValues = [];
    this.averages = [];
    this.completionCallback = null;
    this.registrationCallback = null;
    this.initEncryptionCallback = null;
    this.statusCallback = null;
    this.enc = new EncryptUtils();
    this.currentAgg = "";
    this.currentTarget = 0;
    this.isPending = false;
  }

  initEncryption() {
    this.log("Initializing encryption");
    return new Promise((completed) => {
      this.enc.init(this).then(data => completed(data));
    });
  }

  log(message) {
    if (this.statusCallback != null) {
      this.statusCallback({"eventType":"log","message": message});
    }
  }

  async encrypt(payload, pubKey) {
    const encrypted_content = await this.enc.encrypt(payload,pubKey);
    return encrypted_content;
  }

  exportKey() {
    return this.enc.exportKey();
  }
  decodeKey(key) {
    return this.enc.decodeKey(key);
  }
  encodePub(pub) {
    return this.enc.encodePub(pub);
  }

  async decrypt(payload) {
    const decrypted_content = await this.enc.decrypt(payload);
    return decrypted_content;
  }
  
  pub(index) {
     return this.registrationMap[index]["pub_key"]
  }

  isInitiator() {
    return this.index == 1;
  }

  getStatus() {
    let payload = {"group": this.group, "node": this.index, "pending": this.isPending && !this.isInitiator()};
    return fetch('/status',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json());
  }

  genPubKeyUuid(pubKey) {
    var payload = {"pk": pubKey};
    return fetch('/genpk',{method: 'POST',body: JSON.stringify(payload)}).then(response => response.text());
  }

  getPubKeyByUuid(uuid) {
    return fetch('/pk/' + uuid).then(response => response.text());
  }

  register(pubKey) {
    var payload = {"pub_key": pubKey,
                   "group": this.group};
    fetch('/register',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => this.handleRegister(data));
    return new Promise((completed) => {this.registrationCallback = completed});

  }

  get_registration() {
    var payload = {"pub_key": this.enc.publicKey,
                   "group": this.group};
    fetch('/get_registration',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => this.handleRegistration(data));
    return new Promise((completed) => {this.registrationCallback = completed});
  }

  handleRegister(data) {
    console.log("Got index " + this.index); 
    if (this.registrationCallback != null) {
      this.registrationCallback(this.index);
    }
  }

  handleRegistration(data) {
    this.index = data["index"];
    console.log("Got index " + this.index); 
    if (this.registrationCallback != null) {
      this.registrationCallback(this.index);
    }
  }

  startAggregation(aggregationValues, excludeInitiator = false) {
    this.excludeInitiator = excludeInitiator;
    this.aggregationValues = aggregationValues;
    console.log("Aggregation values");
    console.log(aggregationValues);
    this.log("Starting aggregation process");
    var payload = {"group": this.group};
    fetch('/get_registrations',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => this.handleGetRegistrations(data));
    return new Promise((completed) => {this.completionCallback = completed});
  }

  setStatusCallback(statusCallback) {
    this.statusCallback = statusCallback;
  }

  getRegistrations() {
    return new Promise((completed) => {
      var payload = {"group": this.group};
      fetch('/get_registrations',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => completed(data));
    });
  }


  handleGetRegistrations(data) {
    this.registrations = Object.keys(data).length;
    this.registrationMap = data;
    this.doAggregate();
  }
  doAggregate() {
    if (this.isInitiator()) {
        this.submitInitialAggregate();
    } else {
        this.waitForAggregate(this.processAggregate.bind(this));
    }
  }
  getRandom() {
    return Math.floor(Math.random() * 100000000)/10000;
  }

  getInitialAgg() {
    var vals = this.aggregationValues;
    var agg = "";
    var sep = "";
    this.initiatorRandoms = [];
    for (var i=0; i < vals.length; i++) {
       this.initiatorRandoms.push(this.getRandom());
       agg += sep + (vals[i] + this.initiatorRandoms[i]);
       sep = " ";
    }
    if (this.statusCallback != null) {
       this.statusCallback({"eventType":"aggregation",
                         "aggregationType":"secret",
                         "aggregate": this.initiatorRandoms});
    }
    return agg;
  }

  async submitInitialAggregate() {
    var agg = this.getInitialAgg();
    let to_index = this.nextIndex();
    this.log("Posting initial value and encrypting with PK" + to_index);
    this.currentAgg = agg;
    this.currentTarget = to_index;
    agg = await this.encrypt(agg,this.pub(to_index));
    var payload = {"from_node": this.index,
                   "to_node": to_index,
                   "group": this.group,
                   "aggregate": agg};
    fetch('/post_aggregate',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => this.waitForAggregate(this.computeAverage.bind(this)));
    if (this.statusCallback != null) {
      this.statusCallback({"eventType": "text", "status":"Submitted and Initiated"});
      this.statusCallback({"eventType":"aggregation",
                         "aggregationType":"sent",
                         "aggregate": this.currentAgg.split(" ")});
      this.statusCallback({"eventType":"aggregation",
                         "aggregationType":"encrypted",
                         "aggregate": ["PK" + to_index]});

    }
  }

  async computeAverage(data) {
    if ("status" in data && data["status"] == "empty") {
      this.waitForAggregate(this.computeAverage.bind(this));
      return;
    }
    var agg = await this.decrypt(data["aggregate"]);
    this.isPending = false;
    this.log("Received final aggregate and computing and posting averages");
    console.log("Received decrypted payload " + agg);
    var aggs = agg.split(" ");
    var averages = [];
    var totalSubmitted = data["posted"];
    if (this.excludeInitiator) {
      totalSubmitted -= 1;
    }
    for (var i=0; i < aggs.length; i++) {
     averages.push((Number(aggs[i]) - this.initiatorRandoms[i])/totalSubmitted);
    }
    var payload = {"node": this.index,
                   "group": this.group,
                   "average": averages};
    fetch('/post_average',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => console.log(data));
    this.averages = averages;
    this.completionCallback(this.averages);
    if (this.statusCallback != null) {
      this.statusCallback({"eventType": "text", "status":"Average Posted"});
      this.statusCallback({"eventType":"aggregation",
                         "aggregationType":"received",
                         "aggregate": aggs});
    }
  }

  async waitForAggregate(callback) {
    if (this.isInitiator()) {
      var data = await this.waitForRepost(this.currentAgg,this.currentTarget); 
    }
    var payload = {"node": this.index,
                   "group": this.group};
    this.log("Waiting for aggregate");
    this.isPending = true;
    fetch('/get_aggregate',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => callback(data));
  }
  nextIndex() {
     if (this.index + 1 > this.registrations) {
       return 1;
     }
     return this.index + 1;
  }
  async processAggregate(data) {
    if ("status" in data && data["status"] == "empty") {
      this.waitForAggregate(this.processAggregate.bind(this));
      return;
    } 
    this.isPending = false;
    var vals = this.aggregationValues;
    var agg = await this.decrypt(data["aggregate"]);
    var aggs = agg.split(" ");
    console.log("Received decrypted payload " + agg);
    var aggString = "";
    var sep = "";
    for (var i = 0; i < vals.length; i++) {
      aggString += sep + (Number(aggs[i]) + vals[i]).toFixed(4);
      sep = " ";
    }
    let to_index = this.nextIndex();
    var posted = data["posted"];
    if (to_index == 1 && posted < 3) {
      this.log("Not enough participants, stopping aggregation");
      return;
    }
    this.log("Received aggregate and reposting encryted with PK" + to_index);
    console.log("Posting new payload " + aggString);
    if (this.statusCallback != null) {
       this.statusCallback({"eventType":"aggregation",
                         "aggregationType":"received",
                         "aggregate": aggs});
       this.statusCallback({"eventType":"aggregation",
                         "aggregationType":"sent",
                         "aggregate": aggString.split(" ")});
       this.statusCallback({"eventType":"aggregation",
                         "aggregationType":"encrypted",
                         "aggregate": ["PK" + to_index]});
    }

    this.currentAgg = aggString;
    this.currentTarget = to_index;
    agg = await this.encrypt(aggString, this.pub(to_index));
    var payload = {"from_node": this.index,
                   "to_node": to_index,
                   "group": this.group,
                   "aggregate": agg};
    fetch('/post_aggregate',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => this.waitForAverage(data));
    if (this.statusCallback != null) {
      this.statusCallback({"eventType": "text", "status":"Submitted"});
    }
  }

  async waitFor(path,indata) {
    let retry = true;
    var data;
    while (retry) {
      data = await fetch('/' + path,{method: 'POST',body: JSON.stringify(indata)})
            .then(response => response.json());
      if (data["status"] != "empty") {
         retry = false; 
      } 
    }
    return data;
  }

  async waitForRepost(agg, target) {
    this.log("Check if aggregte was consumed by " + target);
    var data = await this.waitFor("check_aggregate",{"node": target,"group": this.group});
    if (data["status"] == "repost") {
       let repost_to = ((data["repost_to"]-1) % this.registrations)+1;
       console.log("Got repost to " + repost_to);
       this.log("Instructed to repost and re-encrypt with PK" + repost_to);
       var posted = data["posted"];
       if (repost_to == 1 && posted < 3) {
         this.log("Not enough participants, stopping aggregation");
	 return {};
       }

       if (this.statusCallback != null) {
         this.statusCallback({"eventType":"aggregation",
                         "aggregationType":"encrypted",
                         "aggregate": ["PK" + repost_to]});
       }

       let enc = await this.encrypt(agg, this.pub(repost_to));
       let payload = {"from_node": this.index,
                      "to_node": repost_to,
                      "group": this.group,
                      "aggregate": enc};
       data = await fetch('/post_aggregate',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json());
       data = await this.waitForRepost(agg, repost_to);
    } else if (data["status"] != "empty") {
       this.log("Posted aggregate consumed");
       console.log("Aggregate consumed for node " + target);
    }
    return data;
  }
   

  async waitForAverage(data) {
    this.log("Waiting for average");
    var data = await this.waitForRepost(this.currentAgg,this.currentTarget); 
    var payload = {"node": this.index,
                   "group": this.group}
    fetch('/get_average',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => this.handleAverage(data));
  }
  
  handleAverage(data) {
    if ("status" in data && data["status"] == "empty") {
      this.waitForAverage(null);
      return;
    }
    this.log("Got average");
    this.averages = data["average"];
    this.completionCallback(this.averages);
  }

}

class PollDB {
  constructor(account) {
    this.account = account;
  }
  create_poll(title,description,email,questions) {
    return new Promise((completed) => {
      var poll = {"title": title, "description": description, "email": email, "questions": questions};
      var payload = {"poll": poll, "account": this.account};
      fetch('/create_poll',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => completed(data));
    });
  }
  list_polls() {
    return new Promise((completed) => {
      var payload = {"account": this.account};
      fetch('/polls',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => completed(data));
    });
  }
  get_poll(poll_id) {
    return new Promise((completed) => {
      var payload = {"poll_id": poll_id};
      fetch('/get_poll',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => completed(data));
    });
  }
  remove_poll(poll_id) {
    return new Promise((completed) => {
      var payload = {"poll_id": poll_id, "account": this.account};
      fetch('/remove_poll',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => completed(data));
    });
  }
  remove_registration(pub_key,poll_id) {
    return new Promise((completed) => {
      var payload = {"pub_key": pub_key, "poll_id": poll_id};
      fetch('/remove_registration',{method: 'POST',body: JSON.stringify(payload)})
            .then(response => response.json())
            .then(data => completed(data));
    });
  }
}

class EncryptUtils {
  constructor() {
     window.PkiCertificateCreated = this.certCreated.bind(this);
     window.PkiPrivateKeyCreated = this.keyCreated.bind(this);
     window.PkiEncryptionCompleted = this.encryptDone.bind(this);
     window.PkiDecryptionCompleted = this.decryptDone.bind(this);
     window.PassEncryptionCompleted = this.passEncryptDone.bind(this);
     window.PassDecryptionCompleted = this.passDecryptDone.bind(this);
     window.GotPassphrase = this.gotPassphrase.bind(this);
     window.ClearKey = this.clearKey.bind(this);
     this.publicKey = null;
     this.privateKey = null;
     this.keyCallback = null;
     this.encCallback = null;
     this.decCallback = null;
     this.passphrase = null;
     this.passphraseCallback = null;
     this.initCallback = null;
     this.publicKey = localStorage.getItem("spokePublicKey");
     this.encryptedPrivateKey = localStorage.getItem("spokePrivateKey");
     // should decrypt this with passphrase

     let el = document.getElementById("hiddenPub");
     // needed for PKI cert encoding
     if (el == null) {
        this.createHiddenElements();
     }
  }

  init(logger) {
    this.logger = logger;
    return new Promise((completed) => {
    this.initCallback = completed;
    if (!this.hasCertificate()) {
      this.logger.log("Generating certificate");
      this.generateKey(); 
    } else {
      this.logger.log("Initiating passphrase");
      this.initPassphrase().then(data => function() {console.log("Got pass")}); 
    }
    });
  }
  hasCertificate() {
    return this.publicKey != null;
  }
  initPassphrase() {
     return new Promise((completed) => {
       this.passphraseCallback = completed;
       getPassphrase();
     });
  }
  clearKey() {
    localStorage.removeItem("spokePrivateKey");
    localStorage.removeItem("spokePublicKey");
    window.location.reload();
  }
  gotPassphrase() {
    let pass = document.getElementById("passphrase").value;
    this.passphrase = pass;
    console.log("Got passphrase"); 


    if (this.encryptedPrivateKey != null) {
      console.log("Decrypting private key"); 
      PassEnvelopedDecrypt(this.encryptedPrivateKey, pass).catch(function(error) {
          document.getElementById("main").setAttribute("hidden","");
          document.getElementById("pass").removeAttribute("hidden");
          alert("Failed to decrypt private key with passphrase. Try again");
      });
    } else {
       document.getElementById("pass").setAttribute("hidden","");
       document.getElementById("main").removeAttribute("hidden");
    }
    if (this.passphraseCallback != null) {
       this.passphraseCallback(this.passphrase);
    }
  }
  passEncryptDone(content) {
    document.getElementById("hiddenEncPriv").innerHTML = content;
    content = document.getElementById("hiddenEncPriv").innerHTML;
    localStorage.setItem("spokePrivateKey", content);
     if (this.initCallback != null) {
         this.initCallback(content);
     }
  }
  passDecryptDone(content) {
     this.logger.log("Decrypted private key");
     this.privateKey = content;
     document.getElementById("pass").setAttribute("hidden","");
     document.getElementById("main").removeAttribute("hidden");
     if (this.initCallback != null) {
         console.log("Calling init complete");
         this.initCallback(content);
     }
  }
  createHiddenElements() {
    var divPub = document.createElement("div");
    divPub.setAttribute("id","hiddenPub");
    divPub.setAttribute("hidden","");
    const b = document.body;
    b.appendChild(divPub);
    var divPriv = document.createElement("div");
    divPriv.setAttribute("id","hiddenPriv");
    divPriv.setAttribute("hidden","");
    b.appendChild(divPriv);
    var divEncPriv = document.createElement("div");
    divEncPriv.setAttribute("id","hiddenEncPriv");
    divEncPriv.setAttribute("hidden","");
    b.appendChild(divEncPriv);

  };
  certCreated(cert) {
    this.publicKey = cert;
  };
  keyCreated(key) {
    this.privateKey = key;
    document.getElementById("hiddenPub").innerHTML = this.publicKey;
    document.getElementById("hiddenPriv").innerHTML = this.privateKey;
    this.publicKey = document.getElementById("hiddenPub").innerHTML;
    this.privateKey = document.getElementById("hiddenPriv").innerHTML;

    localStorage.setItem("spokePublicKey", this.publicKey);
    this.logger.log("Getting passphrase");
    this.initPassphrase().then(data => PassEnvelopedEncrypt(this.privateKey, data));
    if (this.keyCallback != null) {
      this.keyCallback({"publicKey":this.publicKey, "privateKey":this.privateKey});
    }
  };
  encryptDone(encryptedText) {
    this.encCallback(encryptedText);
  };
  decryptDone(decryptedText) {
    console.log("Decrypted result " + decryptedText);
    this.decCallback(decryptedText);
  };
  generateKey() {
    return new Promise((completed) => {
      this.keyCallback = completed;
      PkiCreateCertificate();
    });
  }
  encrypt(text, pubKey=null) {
    if (pubKey == null) {
       console.log("No pubkey passed, encrypting with self");
       pubKey = this.publicKey;
    }
    return new Promise((completed) => {
    if (pubKey == null) {
       completed(null);
       return;
    } 
    this.encCallback = completed;
    console.log("Encrypting with: " + pubKey);
    PkiEnvelopedEncrypt(pubKey,text);
    });
  } 

  exportKey() {
     return btoa(this.publicKey);
  }

  decodeKey(key) {
     return atob(key);
  }
  encodePub(pub) {
     return btoa(pub);
  }

  decrypt(text) {
    return new Promise((completed) => {
      if (this.privateKey == null) {
          completed(null);
          return;
      }
      console.log("Decrypting with public: " + this.publicKey);
      console.log("Decrypting with private: " + this.privateKey);
      console.log("Decrypting text: " + text);
      this.decCallback = completed;
      PkiEnvelopedDecrypt(this.publicKey,this.privateKey, text);
    });
  } 

}

function getPassphrase() {
   console.log("Getting passphrase");
   document.getElementById("pass").removeAttribute("hidden");
}
