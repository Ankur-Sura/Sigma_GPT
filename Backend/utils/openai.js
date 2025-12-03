// =============================================================================
//                     OPENAI UTILITY - API Wrapper Functions
// =============================================================================
/**
 * 📚 WHAT IS THIS FILE?
 * ---------------------
 * Utility functions for calling OpenAI's Chat Completions API.
 * 
 * 🔗 FUNCTIONS:
 * -------------
 * getOpenAIAPIResponse()         → Main chat function with history
 * getOpenAIAPIResponseWithContext() → RAG function with document context
 * 
 * 📌 OPENAI CHAT COMPLETIONS API:
 * --------------------------------
 * Endpoint: https://api.openai.com/v1/chat/completions
 * Model: gpt-4o-mini (fast, cheap, good quality)
 * 
 * 📌 MESSAGE ROLES:
 * -----------------
 * - system: Instructions for the AI (persona, rules)
 * - user: Human messages
 * - assistant: AI responses
 * 
 * 📌 INTERVIEW TIP:
 * -----------------
 * "I use OpenAI's Chat Completions API with a system prompt that defines
 *  the AI's behavior. I include conversation history for context and
 *  handle date/time specially to avoid hallucinations."
 */

import "dotenv/config";
// 📖 Loads OPENAI_API_KEY from .env file


// =============================================================================
//                         DATE/TIME UTILITIES
// =============================================================================
/**
 * 📖 Why Date Utilities?
 * ----------------------
 * LLMs have a training cutoff date and can hallucinate wrong dates.
 * These functions ensure accurate date/time responses.
 * 
 * 📌 PROBLEM: "What's today's date?" → LLM might say wrong date
 * 📌 SOLUTION: Inject current date in system prompt + shortcut date questions
 */

const dateInfo = () => {
    // 📖 Gets current date in multiple formats
    const now = new Date();
    const isoDate = now.toISOString().split("T")[0];
    // 📖 ISO format: "2024-01-15"
    
    const local = now.toLocaleString("en-US", {
        timeZone: process.env.TZ || "UTC",
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
    });
    // 📖 Local format: "Monday, January 15, 2024, 14:30"
    
    const utc = now.toUTCString();
    // 📖 UTC format: "Mon, 15 Jan 2024 14:30:00 GMT"
    
    return {isoDate, local, utc};
};

const answerWithCurrentDate = () => {
    // 📖 Quick response for date questions (no API call needed)
    const {isoDate, local, utc} = dateInfo();
    return `Today's date is ${isoDate}. Local time: ${local}. UTC: ${utc}.`;
};

const needsDateOnly = (message = "") => {
    // 📖 Regex to detect simple date questions
    // 📌 WHY SHORTCUT?
    // - Faster (no API call)
    // - Always accurate (no LLM hallucination)
    // - Cheaper (no tokens used)
    return /\b(current\s+date|current\s+day|today'?s?\s+date|what'?s\s+the\s+date|what\s+day\s+is\s+it)\b/i.test(message);
};


// =============================================================================
//                         SYSTEM PROMPT (MAM Style)
// =============================================================================
/**
 * 📖 Custom Teaching Style Prompt
 * -------------------------------
 * This prompt makes the AI explain things in a structured, teacher-like way.
 * Great for learning and interview prep!
 * 
 * 📌 WHY A CUSTOM PROMPT?
 * - Consistent response format
 * - Better for learning (step-by-step)
 * - Covers edge cases and mistakes
 */

const MAM_PROMPT = `
When the user gives you dictation of their video lectures or any topic, you must ALWAYS follow this fixed Mam-style explanation format.

1) Concept: explain in clear English, stay 85–90% close to the user wording.
2) Code: if code exists, show full clean code block.
3) Line-by-line explanation: what/why/what breaks if removed.
4) Implementation/Output: describe what happens when it runs.
5) Fix/Edge Cases/Common Mistakes: typical errors and checks.
6) Summary/Recap: short recap (table if helpful).

If no code, explain step-by-step like a teacher. Keep a beginner-friendly tone.
`;


// =============================================================================
//                    MAIN CHAT FUNCTION (with History)
// =============================================================================
/**
 * 📖 getOpenAIAPIResponse(message, history)
 * -----------------------------------------
 * Sends a message to OpenAI with conversation history.
 * 
 * Parameters:
 * - message: Current user message
 * - history: Array of {role, content} from previous turns
 * 
 * Returns: AI response string
 * 
 * 📌 MESSAGE STRUCTURE:
 * [
 *   {role: "system", content: "You are..."},      // Instructions
 *   {role: "user", content: "Hello"},              // History
 *   {role: "assistant", content: "Hi there!"},    // History
 *   {role: "user", content: "New message"}        // Current
 * ]
 * 
 * 📌 WHY HISTORY?
 * LLMs are stateless - they don't remember previous messages.
 * We send the full history so the AI has context.
 */

const getOpenAIAPIResponse = async(message, history = []) => {
    // =================================================================
    // Step 1: Shortcut for Date Questions
    // =================================================================
    if(needsDateOnly(message)) {
        return answerWithCurrentDate();
        // 📌 Skip API call for simple date questions
    }

    // =================================================================
    // Step 2: Build System Prompt with Current Date
    // =================================================================
    const {local, utc} = dateInfo();
    const systemPrompt = `You are a helpful assistant. Today's local time is ${local}. UTC time is ${utc}. If asked for the date or time, use these exact values.\n\n${MAM_PROMPT}`;
    // 📖 System prompt:
    // 1. Sets AI persona ("helpful assistant")
    // 2. Injects current date (prevents hallucination)
    // 3. Adds teaching style instructions

    // =================================================================
    // Step 3: Build Messages Array
    // =================================================================
    const messages = [
        {role: "system", content: systemPrompt},
        // 📖 System message always first
        
        ...(history || []),
        // 📖 Spread history messages
        // 📌 Spread operator (...) flattens array
        
        {role: "user", content: message}
        // 📖 Current message last
    ];

    // =================================================================
    // Step 4: Call OpenAI API
    // =================================================================
    const options = {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`
            // 📖 API key from .env file
            // 📌 NEVER hardcode API keys!
        },
        body: JSON.stringify({
            model: "gpt-4o-mini",
            // 📖 Model choices:
            // - gpt-4o-mini: Fast, cheap, good quality (recommended)
            // - gpt-4o: Most capable, expensive
            // - gpt-3.5-turbo: Older, cheaper
            messages
        })
    };

    try {
        const response = await fetch("https://api.openai.com/v1/chat/completions", options);
        // 📖 OpenAI Chat Completions endpoint
        
        const data = await response.json();
        // 📖 Response structure:
        // {
        //   choices: [{
        //     message: {role: "assistant", content: "..."}
        //   }]
        // }
        
        return data.choices?.[0]?.message?.content || "No answer generated.";
        // 📖 Optional chaining (?.) prevents errors if structure is wrong
    } catch(err) {
        console.log(err);
        return "Error calling OpenAI.";
    }
}


// =============================================================================
//                    RAG FUNCTION (with Document Context)
// =============================================================================
/**
 * 📖 getOpenAIAPIResponseWithContext(question, context)
 * -----------------------------------------------------
 * Sends a question to OpenAI with document context (for RAG).
 * 
 * Parameters:
 * - question: User's question
 * - context: Retrieved document chunks (from vector search)
 * 
 * 📌 RAG FLOW:
 * 1. User asks question about PDF
 * 2. Search vector DB for similar chunks
 * 3. Give chunks to LLM as context
 * 4. LLM answers grounded in the document
 * 
 * 📌 WHY RAG?
 * - LLMs can hallucinate facts
 * - RAG grounds answers in real documents
 * - User can verify information
 */

const getOpenAIAPIResponseWithContext = async(question, context) => {
    const {local, utc} = dateInfo();
    
    const systemPromptText = `You are a helpful assistant. Today's local time is ${local}. UTC time is ${utc}. Answer using ONLY the provided context. If the context is insufficient, say you do not have enough information.\n\n${MAM_PROMPT}`;
    // 📖 Key instruction: "Answer using ONLY the provided context"
    // 📌 This prevents hallucination - AI can only use given info
    
    const options = {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`
        },
        body: JSON.stringify({
            model: "gpt-4o-mini",
            messages: [
                {
                    role: "system",
                    content: systemPromptText
                },
                {
                    role: "assistant",
                    content: `Context:\n${context}`
                    // 📖 Provide context as assistant message
                    // 📌 Alternative: Could use "user" role with clear labeling
                },
                {
                    role: "user",
                    content: question
                }
            ]
        })
    };

    try {
        const response = await fetch("https://api.openai.com/v1/chat/completions", options);
        const data = await response.json();
        return data.choices?.[0]?.message?.content || "No answer generated.";
    } catch(err) {
        console.log(err);
        return "Error calling OpenAI with context.";
    }
}


// =============================================================================
//                              EXPORTS
// =============================================================================

export {getOpenAIAPIResponseWithContext};
// 📖 Named export for RAG function

export default getOpenAIAPIResponse;
// 📖 Default export for main chat function
// 
// 📌 USAGE:
// import getOpenAIAPIResponse from "./utils/openai.js"
// import { getOpenAIAPIResponseWithContext } from "./utils/openai.js"


// =============================================================================
//                         SUMMARY FOR INTERVIEWS
// =============================================================================
/**
 * 📌 OPENAI API CONCEPTS:
 * 
 * 1. CHAT COMPLETIONS API:
 *    - Endpoint: /v1/chat/completions
 *    - Messages: [{role, content}, ...]
 *    - Roles: system, user, assistant
 * 
 * 2. SYSTEM PROMPT:
 *    - Sets AI behavior and persona
 *    - Include current date to prevent hallucination
 *    - Custom instructions for response format
 * 
 * 3. CONVERSATION HISTORY:
 *    - LLMs are stateless
 *    - Send previous messages for context
 *    - Token limit applies to total context
 * 
 * 4. RAG INTEGRATION:
 *    - Provide document context in messages
 *    - Instruct to only use provided context
 *    - Prevents hallucination with grounding
 * 
 * 📌 API KEY SECURITY:
 * - Store in .env file
 * - Never commit to git
 * - Use environment variables in production
 */
