from fastapi import FastAPI, Query, Path
from .queue.connection import queue
from .queue.worker import process_query

app = FastAPI()

@app.get('/')
def root():
    return {"status": 'Server is up and running'}

@app.post('/chat')
def chat(query: str = Query(..., description="Chat Message")):  # Here we have defined a function which take input as string and it is necessary to provide query else FastApi will through an error
    # Query ko Queue mei daal do
    job = queue.enqueue(process_query,query) # we have used queue because in connection.py file we have given name queue. here process_query will call function with parameter query
    # Here we have entered our query in queue using this commmand and here enqueue will create an object which will return: 1. job.id which is unique ,
    #                                                                                                                       2. job.status --> queued/started/finished
    #                                                                                                                       3. job.return_value → final RAG answer                                                
    # FastAPI immediately replies to frontend: That your Job is received nd this is your job.id , Hence the issue to Request Timeout will be resolved  
    return {"status": "queued", "job_id": job.id}

@app.get("/result/{job_id}")
def get_result(job_id: str = Path(..., description="Job ID")):
    job = queue.fetch_job(job_id=job_id)
    result = job.return_value()

    return {"result": result}
