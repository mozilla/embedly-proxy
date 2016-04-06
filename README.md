# Embedly Proxy

A simple python/flask app which proxies requests to the embed.ly service and masks the
application API key.

## Build
[![Circle CI](https://circleci.com/gh/mozilla/embedly-proxy/tree/master.svg?style=svg)](https://circleci.com/gh/mozilla/embedly-proxy/tree/master)

# API Interface

Extract V1
----

  This V1 API is no longer supported.

Extract V2
----
  Extract metadata from a provided list of URLs.

* **URL**

  https://embedly-proxy.dev.mozaws.net/v2/extract

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

        $.ajax({
          url: "https://embedly-proxy.dev.mozaws.net/v2/extract,
          type : "POST",
          dataType: "json",
          contentType : "application/json",
          data: JSON.stringify({
            urls: [
              'https://www.mozilla.org/',
              'https://developer.mozilla.org/en-US/docs/Web/JavaScript'
            ]
          }),
          success : function(r, data) {
            console.log(data);
          }
        });
