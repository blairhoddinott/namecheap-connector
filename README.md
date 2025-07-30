# namecheap-connector

## Overview

This utility was born out of a need to solve a split-brain DNS issue through automation. 

Essentially, my problem was this: 

I am trying to use cert-manager in k8s I host in an isolated lab environment to generate legit certs I can use in my cluster. This avoids the circus of side-loading certs and re-building dockers to bake certs in places everywhere. As part of my flow, I have the ClusterIssuer generating a TXT record in my primary domain (hosted by NameCheap) for the verification. Unfortunately, the cluster is trying to verify this, and it is behind a private DNS server hosting that zone. THus the split-brain dilemma. 

Long story short, this tool was meant to be able to grab the TXT records from my domain, and feed it into redis to be picked up by a different script I have to populate said record in my technitium DNS server. While working with the NameCheap API, I found it was a pain in the ass (particularly that terrible XML format), and figured some other poor soul would one day have need to interact with this. Thus, here we are.

## Using this tool

I did this as a uv project, which should hopefully make your life easy. Git clone the repo and `uv run src/main.py` (with appropriate arguments) and uv should take care of the versioning and requirements automagically. If you aren't on the uv bandwagon yet, time to hop abord. [uv](https://github.com/astral-sh/uv) is great, and super convenient. It took a lot to get me away from pyenv, but here we are. 

### Pre-reqs

You will need to modify the .env file. Copy the template and fill in the necessary info. The REDIS keys can be left alone, unless you're trying to do something similar to me. If you are, drop me a note and I can hook you up with the other side of this script if I don't release it onto my GitHub by then.

### Supported Commands

Right now, this does the following:

- Query for all records of a specific type `-t <RECORD_TYPE>` in the given domain `-d <domain name>`
- Query for all records in a domain

I may add functionality to add records, depending on what kind of gong show dealing with the stupid XML is. 