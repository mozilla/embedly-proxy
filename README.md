# Embedly Proxy

A simple python/flask app which proxies requests to the embed.ly service and masks the 
application API key.

# API Interface

Extract
----
  Extract metadata from a provided list of URLs.

* **URL**

  http://embedly-proxy.dev.mozaws.net/extract

* **Method:**

  `GET`

*  **URL Params**


  * **urls**

    The URLs from which to extract metadata.
    They should appear unencoded, and may include protocol.

    ex: `urls=http://www.mozilla.com&urls=developer.mozilla.org`

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
