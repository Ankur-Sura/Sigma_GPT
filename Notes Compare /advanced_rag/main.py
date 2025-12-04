from advanced_rag.server import app
import uvicorn
from dotenv import load_dotenv

load_dotenv()

def main():
    uvicorn.run(app, port=8000, host="0.0.0.0")

main()

"""
✅ Full Explanation

from dotenv import load_dotenv
load_dotenv()

✔ What it does:

It loads all variables from your .env file into the system environment.

✔ Why needed?

uvicorn.run(app, port=8000, host="0.0.0.0")

✔ What is Uvicorn?

Uvicorn is the server that runs your FastAPI backend.

FastAPI itself is just code.
Uvicorn is what actually serves the API to the browser.


Why host="0.0.0.0"?

This is very important.

Meaning:

0.0.0.0 = listen on all network interfaces.

✔ Required when running inside Docker
✔ Required if other services (Redis, Qdrant) need to talk to it
✔ Required if you want to access your backend from outside

If you wrote:

host="127.0.0.1"

👉 Only your laptop could access it
👉 Other containers cannot reach it
👉 Docker networking will break

So:

0.0.0.0 = Open for other containers (Redis, Qdrant, Frontend) to connect


Why call it inside main()?

This pattern:

def main():
    uvicorn.run(...)
main()

Is just a clean way to structure code.

You could run Uvicorn like this:

uvicorn.run(app)

But using main() is cleaner for:
	•	Deployment
	•	Docker
	•	Gunicorn
	•	Future configuration


🎯 FINAL SIMPLE EXPLANATION

This file is the starter of your FastAPI server.
	•	load_dotenv() → loads environment variables
	•	uvicorn.run(app...) → starts your FastAPI backend
	•	host="0.0.0.0" → allows Docker containers and other devices to reach your app
	•	main() → clean entry-point structure

** Running the FastAPI server means we make a local website (localhost:8000) active.
When we access routes like / or /chat, FastAPI performs the logic written inside those route functions.

"""
