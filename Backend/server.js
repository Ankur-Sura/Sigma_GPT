// =============================================================================
//                     SIGMA GPT - BACKEND SERVER (Node.js + Express)
// =============================================================================
/**
 * 📚 WHAT IS THIS FILE?
 * ---------------------
 * This is the MAIN entry point for your Node.js backend.
 * It creates an Express server that:
 * 1. Connects to MongoDB (for storing chat threads)
 * 2. Sets up API routes (chat, PDF, tools)
 * 3. Listens on port 8080 for incoming requests from Frontend
 * 
 * 🔗 ARCHITECTURE:
 * ----------------
 *     Frontend (React:5173) → Backend (Express:8080) → AI Service (FastAPI:8000)
 *                                   ↓
 *                              MongoDB (Database)
 * 
 * 📌 WHY EXPRESS.JS?
 * ------------------
 * Express is the most popular Node.js web framework:
 * - Simple routing (app.get, app.post, etc.)
 * - Middleware support (cors, json parsing)
 * - Easy to integrate with databases
 * 
 * 📌 INTERVIEW TIP:
 * -----------------
 * "My backend uses Express.js to handle API requests from React frontend,
 *  stores data in MongoDB, and proxies AI requests to a Python FastAPI service."
 */

// =============================================================================
//                              IMPORTS
// =============================================================================

import express from "express";
// 📖 express: The web framework for Node.js
// Creates our server and handles HTTP requests

import "dotenv/config";
// 📖 dotenv/config: Loads environment variables from .env file
// This gives us access to MONGODB_URI, OPENAI_API_KEY, etc.
// 📌 Why? Keeps secrets out of code, different values for dev/prod

import cors from "cors";
// 📖 cors: Cross-Origin Resource Sharing middleware
// 📌 Why? Allows Frontend (localhost:5173) to call Backend (localhost:8080)
// Without this, browser blocks requests between different origins (ports)

import mongoose from "mongoose";
// 📖 mongoose: MongoDB ODM (Object Document Mapper)
// 📌 Why? Provides schema validation, easy queries, connection pooling
// Think of it as an "ORM for MongoDB"

import chatRoutes from "./routes/chat.js";
// 📖 Chat routes: Handles /api/chat, /api/thread endpoints
// Where conversation logic lives

import pdfRoutes from "./routes/pdf.js";
// 📖 PDF routes: Handles /api/upload-pdf, /api/pdf-query
// Proxies to Python AI service for RAG (PDF Q&A)

import toolRoutes from "./routes/tools.js";
// 📖 Tool routes: Handles /api/search, /api/stt, /api/image-ocr
// Proxies to Python AI service for web search, speech-to-text, OCR


// =============================================================================
//                         EXPRESS APP SETUP
// =============================================================================

const app = express();
// 📖 Creates the Express application instance
// This is the core of your backend server

const PORT = 8080;
// 📖 The port where server listens
// Frontend calls http://localhost:8080/api/...


// =============================================================================
//                            MIDDLEWARE
// =============================================================================
/**
 * 📚 WHAT IS MIDDLEWARE?
 * ----------------------
 * Middleware = Functions that run BEFORE your route handlers
 * They can modify request/response, add features, or block requests
 * 
 * Order matters! Middleware runs in the order you define them.
 */

app.use(express.json());
// 📖 Parses JSON request bodies
// When Frontend sends: { "message": "Hello" }
// This middleware makes it available as req.body.message
// 📌 Without this, req.body would be undefined!

app.use(cors());
// 📖 Enables CORS for all origins
// 📌 Why needed?
// - Frontend runs on localhost:5173
// - Backend runs on localhost:8080
// - Browser blocks "cross-origin" requests by default
// - This middleware adds headers to allow it


// =============================================================================
//                           ROUTE MOUNTING
// =============================================================================
/**
 * 📚 WHAT IS ROUTE MOUNTING?
 * --------------------------
 * app.use("/prefix", router) mounts a router at a path prefix
 * 
 * Example:
 * - chatRoutes has: router.post("/chat", ...)
 * - Mounted at: app.use("/api", chatRoutes)
 * - Full URL becomes: POST /api/chat
 */

app.use("/api", chatRoutes);
// 📖 Mounts chat routes under /api
// Endpoints: /api/chat, /api/thread, /api/thread/:threadId

app.use("/api", pdfRoutes);
// 📖 Mounts PDF routes under /api
// Endpoints: /api/upload-pdf, /api/pdf-query
// These proxy to Python AI service for RAG functionality

app.use("/api", toolRoutes);
// 📖 Mounts tool routes under /api
// Endpoints: /api/search, /api/stt, /api/image-ocr
// These proxy to Python AI service for various AI tools


// =============================================================================
//                          SERVER STARTUP
// =============================================================================

app.listen(PORT, () => {
    console.log(`server running on ${PORT}`);
    connectDB();
});
// 📖 Starts the HTTP server
// - PORT: Which port to listen on (8080)
// - Callback: Runs after server starts
// - connectDB(): Connects to MongoDB after server is up
//
// 📌 INTERVIEW TIP:
// "The server starts listening for HTTP requests, then establishes
//  the database connection. This ensures the port is available before
//  spending time on DB connection."


// =============================================================================
//                        DATABASE CONNECTION
// =============================================================================

const connectDB = async() => {
    try {
        await mongoose.connect(process.env.MONGODB_URI);
        // 📖 Connects to MongoDB using connection string from .env
        // process.env.MONGODB_URI = "mongodb://localhost:27017/sigma_gpt"
        //
        // 📌 Why async/await?
        // Database connection is asynchronous (takes time)
        // We wait for it to complete before continuing
        
        console.log("Connected with Database!");
    } catch(err) {
        console.log("Failed to connect with Db", err);
        // 📌 In production, you might want to:
        // - Retry connection
        // - Exit process (process.exit(1))
        // - Send alert to monitoring
    }
}


// =============================================================================
//                         SUMMARY FOR INTERVIEWS
// =============================================================================
/**
 * 📌 WHAT THIS FILE DOES:
 * 1. Creates Express server on port 8080
 * 2. Enables JSON parsing and CORS
 * 3. Mounts API routes (/api/chat, /api/upload-pdf, etc.)
 * 4. Connects to MongoDB
 * 
 * 📌 KEY CONCEPTS TO EXPLAIN:
 * - Express.js: Web framework for Node.js
 * - Middleware: Functions that process requests before routes
 * - CORS: Allows Frontend to call Backend from different origin
 * - Mongoose: ODM for MongoDB with schema validation
 * - Route mounting: Organizing routes under path prefixes
 * 
 * 📌 ARCHITECTURE:
 * Frontend (React) → Backend (Express) → AI Service (FastAPI)
 *                          ↓
 *                     MongoDB
 */


// app.post("/test", async (req, res) => {
//     const options = {
//         method: "POST",
//         headers: {
//             "Content-Type": "application/json",
//             "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`
//         },
//         body: JSON.stringify({
//             model: "gpt-4o-mini",
//             messages: [{
//                 role: "user",
//                 content: req.body.message
//             }]
//         })
//     };

//     try {
//         const response = await fetch("https://api.openai.com/v1/chat/completions", options);
//         const data = await response.json();
//         //console.log(data.choices[0].message.content); //reply
//         res.send(data.choices[0].message.content);
//     } catch(err) {
//         console.log(err);
//     }
// });
