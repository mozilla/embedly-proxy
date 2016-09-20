# Embedly Proxy

A simple python/flask app which proxies requests to the embed.ly service and masks the
application API key.

## Build
[![Circle CI](https://circleci.com/gh/mozilla/embedly-proxy/tree/master.svg?style=svg)](https://circleci.com/gh/mozilla/embedly-proxy/tree/master)

# API Interface

Extract V1
----

  This V1 API is no longer supported.

Fetch Metadata V2
----
  Fetch metadata for a provided list of URLs from remote metadata services.

* **Service URLs**

  * **Embedly**
  - https://embedly-proxy.services.mozilla.com/v2/extract

  * **Mozilla**
  - https://embedly-proxy.services.mozilla.com/v2/metadata

* **Method:**

  `POST`

*  **URL Params**

  None

* **Data Params**

  * **urls**

    The POST body must be a JSON encoded dictionary with one key: urls
    which contains a list of URLs to be queried.  A maximum of 25 URLs
    may be submitted in one request.

    ex:

      {
        urls: [
          "https://www.mozilla.org/",
          "https://developer.mozilla.org/en-US/docs/Web/JavaScript"
        ]
      }


* **Request Headers**

  The POST body must be a JSON encoded dictionary.

  `content-type: application/json`

* **Success Response:**

  * **Code:** 200

  JSON encoding

      {
        urls: {
          "<url1>": <embedly metadata>,
          "<urln>": <embedly metadata>,
        },
        error: ""
      }

      ex success:

      {
        urls: {
          "https://www.mozilla.org": {
            <embedly metadata>
        },
        error: ""
      }
      
      ex failure:

      {
        urls: {},
        error: "The Content-Type header must be set to application/json"
      }

* **Error Responses:**

  * **Code:** 400

  The server received a malformed request.  

  * **Code:** 500

  The server was unable to satisfy the request.

* **Sample Call:**

        curl -X POST -d '{"urls":["https://www.mozilla.org"]}' -H 'content-type:application/json' https://embedly-proxy.services.mozilla.com/v2/metadata
