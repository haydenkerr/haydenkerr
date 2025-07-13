Hi 👋, I'm Hayden
I’m currently working on building up my GitHub profile with data analytics, scraping and integration projects.

🏭 I have worked in multiple industries over the past 15 years while continually learning.

👨‍💻 All of my data analytics projects are available at https://github.com/haydenkerr/data-analytics

💬 Ask me about anything analytics, documentation, compliance, data visualisation related, and I'll be happy to help you out. 

📫 Reach me LinkedIn. 

☕ When I am not learning, working or being a dad, I am probably standing at my coffee machine so that I can get back to learning, working and being a dad.



Languages and Tools:
git html5 sql python pytorch scikit_learn seaborn excel....with python phroar!

## QR Code Webhook Server

This repository includes a minimal FastAPI application that demonstrates how to receive a webhook and generate a QR code. Incoming requests must use OAuth2 token authentication. The received parameters are turned into a URL which is converted to a QR code. Generated images are stored in `qr_codes/` and served back as static files. Each QR code links to a tracking endpoint so scans can be logged before redirecting the user to the final destination.

### Running locally

Install dependencies and start the server:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

1. Obtain a token using the `/token` endpoint with `username="user@example.com"` and `password="secret"`.
2. Send a POST request to `/webhook` with the token in the `Authorization` header.

The response contains the path to the generated QR code image as well as the tracking URL encoded in the QR code. Visiting this URL will log the request and redirect to the final destination.
