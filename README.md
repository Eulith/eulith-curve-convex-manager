# Eulith Curve/Convex Manager

This repo contains an end to end example of using the Eulith python client to do position management
on Curve and Convex. Using this software instead of managing your position on via the Curve & Convex UIs comes
with several advantages:
1. **Compounding is automated**. Calculate the optimal compound schedule and let it run on its own ad-infinitum
2. Mitigate security pitfalls built into the UI such as "infinity approvals." This software only approves exactly
how much is needed for each transaction. No cleanup required afterward.
3. Manage multiple positions all from the same place

# Run
The code contained in this repo is designed to be an example. Modifications will need to be made to put this in production.

## 1. `./setup.sh <EULITH_REFRESH_TOKEN>`

If you don't know what your `<EULITH_REFRESH_TOKEN>` is, you can get it 
by logging into https://eulithclient.com. Note this should be the REFRESH token, NOT
the access token.

This command sets up the appropriate configuration and creates 
a new wallet if you have not already specified one. Note that this will not overwrite
the existing private key! So if you accidentally run this twice you can still 
recover the private key being used in `utils/settings.py`.

NOTE: to be clear, this commands creates a new wallet. We just want you to see the
demo so we create a new wallet for you and ask you to send it a little ETH for 
experimentation.

WE DO NOT HAVE ACCESS TO THIS NEWLY CREATED WALLET UNLESS YOU SEND IT TO US

## 2. `./run.sh`
Boom. That's it. 

This will fail if you don't have sufficient balance in the wallet to 
run the example (it will be obvious and ask you to send some ETH).

Otherwise, you'll see the example position management working and you can
view the transactions that it's executing on your behalf.
