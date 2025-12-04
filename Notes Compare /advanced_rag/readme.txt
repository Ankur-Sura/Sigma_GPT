Step-by-Step Execution Guide
Here is exactly what happens in your code, file by file:

1. Initialization (Infrastructure)
File: docker-compose.yml
Action: You run docker compose up.
What happens:
Starts Valkey (Redis) on port 6379 (Used to store the job queue).
Starts Qdrant on port 6333 (Used to store vector embeddings of your PDF).

2. Starting the Server
File: main.py
Action: You run python main.py.
What happens:
Calls uvicorn.run(app, ...) to start the FastAPI web server on http://localhost:8000.
The app object is imported from server.py.

3. User Sends a Request
File: server.py
Endpoint: @app.post('/chat')
Action: User sends POST http://localhost:8000/chat?query=What is node?
Execution:
chat(query) function is called.
queue.enqueue(process_query, query) is executed.
This connects to Redis using advanced_rag/queue/connection.py.
It serializes (packages up) the function process_query and the argument "What is node?".
It pushes this package into the Redis list named default.
The server immediately returns a job_id (e.g., abc-123) to the user.
Note: The API request is now finished. The user is free to go do other things.

4. Worker Picks Up the Job
File: start_worker.sh (calls rq worker)
Action: The worker is running in the background loop.
Execution:
The worker sees a new item in the Redis default queue.
It pulls the item out and sees it needs to run advanced_rag.queue.worker.process_query.

5. Processing the Query
File: advanced_rag/queue/worker.py
Function: process_query(query)
Execution:
Vector Search: Calls vector_db.similarity_search(query).
Connects to Qdrant (Docker).
Finds the most relevant text chunks from your indexed PDF.
Context Building: Loops through results and creates a string:
"Page Content: ... Page Number: 11 ..."
LLM Call: Sends the User Query + Retrieved Context to OpenAI (gpt-4.1).
Result: OpenAI returns the answer (e.g., "Node.js is a runtime...").
Return: The function returns this string.

6. Saving the Result
System: RQ Worker
Action: The worker takes the return value from step 5 and saves it back into Redis under the key rq:job:abc-123.

7. User Gets the Result
File: server.py
Endpoint: @app.get("/result/{job_id}")
Action: User sends GET http://localhost:8000/result/abc-123

Execution:
queue.fetch_job(job_id) looks up the job in Redis.
job.return_value retrieves the saved string from Step 6.
Returns {"result": "Node.js is a runtime..."} to the user.