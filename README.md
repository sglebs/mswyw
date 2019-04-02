# mswyw - Microservice: Worth Your Weight?

## What it is

A little utility that gathers some metrics about your deployed services and computes 1 metric - mswyw. 
It quantifies if your microservice is worth its weight. The formula is simple:

mswyw = VALUE / COST

Examples of *VALUE* attributes:

* Number of endpoints (presumably the more endpoints, the more functionality, the more useful. Controversial)
* Number of User Story Points it implements (a measure of features/value to the user)
* Number of Function Points it implements (a measure of features/value to the user)
* APDEX - a measure of user satisfaction with the performance of your (micro)service
* Error Rate - a measure of user insatisfaction with your service
* Average response time - the faster your service responds, the happier the consumers will be.
  
Examples of *COST* attributes:

* Total amount of RAM used by all replicas of your (micro)service. You know that Amazon charges for that, right?
* Total amount of vCPUs used by all your replicas. You also pay for that.



## Motivation

Use and abuse of microservices is intense lately. I have seen my fair share of convoluted, bloated Dockerfiles, 
not to mention REST microservices that eat 300MB RAM and with one single endpoint, which tells if a person's 
document ID is well formed. You know, the kind of thing you do with 20 lines of code. This kind of utility is 
much better suited for a reusable library. If it is to be shared by many projects... sure, go ahead and make it 
into a separate git repo and produce a binary JAR (if in Java) which people can import. It does *not* need to 
be a microservice.

I agree with Bob Martin that one should be able to defer the deploy decision. I should be able to deploy code 
with a REST façade of 20 endpoints or as 2 services each with a REST façade of 10 endpoints each. Or with a SOAP 
façade. Or both. Or GraphQL. You get the idea - don't hardcode the façade technology into your reusable core. 
Read about hexagonal architecture, for example.

By obtaning a metric we hope to let people compare the "fat factor" of their (micro)services.

## How to install

*** pip install

## How to run

You need to tell mswyw how to gather runtime information (RAM, APDEX etc) by informing the name of a provider, 
in the form of a fully qualified name of a Python module that implements the API we need.
If, instead, the value you provide is a literal json, we will use that instead. If the value is a valid file path, 
we assume it is a json file with the values we need.

You also need the same for info about the code (lines of code, language, etc). The same applies here about the value 
being either a fully qualified name of a module or a literal json or a json file.

`
mswyw --runtimeProvider=nrelic 
      --codeInfoProvider={"loc":120,"lang":"java"} 
      --providerParams={"nrelic.ACCOUNT":"123456","nrelic.APIKEY":"ABCDEFG"}
`




