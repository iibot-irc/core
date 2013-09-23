core
====

The core of iibot

Prerequisites
=============

* Linux


Setup
=====

Create a new user
-----------------

The iibot software requires a user account to deploy into. This makes a number of things easier. To create a new user account in Linux, you can do

    useradd myfancybot

You probably want to limit the number of processes that your new bot can have running at a time. If you don't it may fork bomb your computer (iibot tends to try this when you write bad code.)
[Here's a link](http://www.cyberciti.biz/tips/linux-limiting-user-process.html) describing how to do it.

From now on, when I use `~/` in a path I will be refering to the homedir of the user account for your bot.

Get the code
------------

Inside your bots home directory, run the following commands:

    git init
    git remote add upstream http://github.com/iibot-irc/core
    git pull upstream master

Your bots installation is managed as a git repo. We add the remote with the name "upstream" because the idea is that you won't need to edit any of the core parts of iibot. You will want to maintain a permanent downstream fork. When there are updates to iibot you can pull them into your fork and they should not interfere with your site-specific modifications. If you need to fix something in the core or generalize something so that it is configurable by downstream forks you are encouraged to push those changes upstream.

Now that we have the core pulled, we need to build ii. Run the following commands in the root of your bots home directory:

    git submodule init
    git submodule update
    cd src/ii
    make DESTDIR=$HOME/opt install
    cd ../../

Initial Configuration
--------------------- 

First, copy `~/etc/iibot.conf.sample` to `~/etc/iibot.conf` and open it up. Change the `user` property to the unix username of your bot and fill in the IRC network details. iibot is only able to connect to one IRC network at this time.

If you run `~/bin/start` now, your bot should connect to the IRC network. You should now look inside the `start` script to understand how it works. Briefly:

0. It loads some config values
1. It makes sure that you are running this script as the correct user (important!)
2. If `~/bin/pre_start` exists, it runs it.
3. It kills the bot if its already running. This script is used if you want to restart the bot as well.
4. It connects to IRC
5. If `~/bin/post_start` exists, it runs it. This is where you join channels, auth with services etc.

Check out the sample `~/bin/post_start.sample`. If your network doesnt have similar services to freenode you may need to change this. Do

    mv ~/bin/post_start.sample ~/bin/post_start

and edit it, and then run `~/bin/start` to reboot the bot. This time it will join your channels, auth with services etc.
