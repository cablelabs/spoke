# SPoKE
Secure Polling and Knowledge Exchange (SPoKE),
is a demonstrator service that allows secure aggregation of
votes without revealing individual votes
even to the service.

The service is based on the [SAFE](https://github.com/cablelabs/safe) mechanism
and was presented in [a CCS Demo](https://dl.acm.org/doi/abs/10.1145/3548606.3563701).

## Getting Started

The Web service requires Python3 and the flask python library.
For example on Ubuntu you can install the dependencies with:
```
apt-get install python3 python3-pip
pip3 install flask
```
Start the server with:
```
python3 server/server.py
```
Then open the following url in a browser:
```
http://localhost:8088/?account=<account>
```
where `<account>` can be replaced with any string (auth not yet implemented).

On the web page enter the `Title` and `Description` of the poll. 
Then enter the `Question` to ask in the poll (currently only one question per poll).
Enter an `Email` where registration requests should be sent and approved. Then
click `Create Poll`. 

The poll should then be listed below. If you click on the poll
link the details will be confirmed and users can be invited to the poll
by email (click `Invite`), or by copying and pasting a poll link (click `Copy Poll Link`) in
a message to users. 

If the users click on the poll link they will be taken to the polling
page. They cannot submit their answer to the question until they register (click Register link).
An email with the public key of the user will be sent to the coordinator who then needs to
verify the email and grant access to the poll by adding the public key in the email
body to registered users (click `Register User`). 

This process could be automated in the future,
but it is important that the email with the public key is verified to be 
coming from a trusted and invited participant. During registration the coordinator
can also associate the public key with a nickname to more easily monitor the aggregation,
and track who participates in different polls.

Note if you expose the server beyond localhost you need to use a https
endpoint for the Copy-links in the Web UI to work.
The easiest way to achieve that is to use ngrok, e.g.:
```
ngrok http 8088
```

## Security design

Whenever a poll is opened a passphrase needs to be entered.
This passphrase is used to encrypt and decrypt private keys before
they are stored in the browser localStorage.
If a certificate is not found a new one will be generated. To enter
into polls the public key needs to be shared with the coordinator.
This sharing is done out-of-band and the identity of the participant
beyond this public key never has to be revealed to the SPOKE server.

Public keys of all participants are known by all participants allowing
each participant to designate an encrypted message to another participant
by encrypting the message with that participant's public key.

Public/Private key encryption as well as symmetric password encryption
is handled by the [PKI.js library](https://pkijs.org/).

Note that the public and private key pair is specific to a browser
as well as the domain of the service. So if you expose the service on
a different ngrok URL a new key pair is generated. The first time
a key pair is generated any passphrase may be picked. The same
passhrase must then be used subsequent times to unlock the key.

Like with the general SAFE mechanism the SPOKE mechanism
assumes that the participants before and after you on the
chain do not collude. The identities of the participants
only have to be known to the poll creator.
There is some trust on the poll creator not to insert
sniffing devices in the chain. This can be avoided by sharing
paricipant public keys and identities across the whole
polling group. Note that if you ask a question and you
know all the participants' answers except one, this mechanism
will also reveal the answer of the last unknown participant.
In general it is hence recommended to have groups significantly
larger than 3 people even though the theoretical limit is 3.

## Failover
If a participants fails to submit a response within 30s of their turn
they will be skipped and the aggregate will be computed without them.
Note that the clock starts ticking from the time the user before you in
the chain has voted.

## TODO
* Initiator who starts but does not vote
* Initiator failover
* Don't expose average unless 3 people voted
