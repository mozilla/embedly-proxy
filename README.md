# Embedly Proxy

A simple python/flask app which proxies requests to the embed.ly service and masks the
application API key.

## Build
[![Circle CI](https://circleci.com/gh/mozilla/embedly-proxy/tree/master.svg?style=svg)](https://circleci.com/gh/mozilla/embedly-proxy/tree/master)

# API Interface

Extract V1
----
  Extract metadata from a provided list of URLs.

* **URL**

  http://embedly-proxy.dev.mozaws.net/extract

* **Method:**

  `GET`

*  **URL Params**


  * **urls**

    The URLs from which to extract metadata.
    They should appear encoded, and may include protocol.

    ex: `urls=https%3A%2F%2Fwww.mozilla.org%2F&urls=https%3A%2F%2Fdeveloper.mozilla.org%2Fen-US%2Fdocs%2FWeb%2FJavaScript`

* **Data Params**

  None

* **Request Headers**

  None

* **Success Response:**

  * **Code:** 200

  JSON encoding

      {
        "<url1>": <embedly metadata>,
        "<urln>": <embedly metadata>,
      }

      ex:

      {
        "https://www.mozilla.org": {
          <embedly metadata>
        }
      }

* **Error Responses:**

  None

* **Sample Call:**

        $.ajax({
          url: "http://embedly-proxy.dev.mozaws.net/extract?urls=mozilla.org&urls=www.mozilla.com",
          dataType: "json",
          type : "GET",
          success : function(r, data) {
            console.log(data);
          }
        });

Extract V2
----
  Extract metadata from a provided list of URLs.

* **URL**

  http://embedly-proxy.dev.mozaws.net/v2/extract

* **Method:**

  `POST`

*  **URL Params**

  None

* **Data Params**

  * **urls**

    The POST body must be a JSON encoded dictionary with one key: urls
    which contains a list of URLs to be queried.

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
          url: "http://embedly-proxy.dev.mozaws.net/v2/extract,
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
