// =============================================================================
//                     APP.JSX - Main React Application Component
// =============================================================================
/**
 * 📚 WHAT IS THIS FILE?
 * ---------------------
 * The root component of the React application.
 * Sets up global state, routing, and layout.
 * 
 * 🔗 COMPONENT HIERARCHY:
 * -----------------------
 *     App (this file)
 *       ├── Sidebar (chat history, navigation)
 *       └── main
 *           └── Routes
 *               ├── ChatWindow (main chat)
 *               ├── Features (features page)
 *               └── Plans (plans page)
 * 
 * 📌 RESPONSIBILITIES:
 * --------------------
 * 1. Define global state (useState hooks)
 * 2. Provide state via Context
 * 3. Set up React Router routes
 * 4. Apply theme (dark/light)
 * 
 * 📌 INTERVIEW TIP:
 * -----------------
 * "App.jsx is my root component. It manages global state like the current
 *  thread, chat history, and theme. I use React Context to share this state
 *  with all child components without prop drilling."
 */

// =============================================================================
//                              IMPORTS
// =============================================================================

import './App.css';
// 📖 Global styles for the app

import Sidebar from "./Sidebar.jsx";
// 📖 Sidebar component: Shows chat history, navigation

import ChatWindow from "./ChatWindow.jsx";
// 📖 Main chat interface component

import {MyContext} from "./MyContext.jsx";
// 📖 React Context for global state sharing

import { useEffect, useState } from 'react';
// 📖 React hooks:
// - useState: Create state variables
// - useEffect: Run side effects (like localStorage)

import {v1 as uuidv1} from "uuid";
// 📖 UUID v1: Time-based unique identifier
// 📌 Why v1? Includes timestamp, good for ordering
// Each new chat gets a unique ID: uuidv1() → "550e8400-e29b-..."

import { Navigate, Route, Routes } from "react-router-dom";
// 📖 React Router components:
// - Routes: Container for route definitions
// - Route: Maps path to component
// - Navigate: Redirect to another route

import Features from "./Features.jsx";
// 📖 Features page component

import Plans from "./Plans.jsx";
// 📖 Plans/pricing page component


// =============================================================================
//                         MAIN APP COMPONENT
// =============================================================================

function App() {
  // ===========================================================================
  // STATE DEFINITIONS (Global State via Context)
  // ===========================================================================
  /**
   * 📌 WHY THESE STATES?
   * 
   * Chat State:
   * - prompt: What user is typing
   * - reply: Last AI response (for animations)
   * - currThreadId: Which conversation is active
   * - prevChats: Messages in current conversation
   * - newChat: Is this a fresh conversation?
   * - allThreads: List for sidebar
   * 
   * UI State:
   * - theme: "dark" or "light"
   */

  const [prompt, setPrompt] = useState("");
  // 📖 Current input field text
  // Used by: ChatWindow input, cleared after send

  const [reply, setReply] = useState(null);
  // 📖 Last AI response
  // Used by: Chat component for typing animation

  const [currThreadId, setCurrThreadId] = useState(uuidv1());
  // 📖 Active conversation ID
  // 📌 Generated with UUID on first load
  // Changes when: User clicks sidebar thread or creates new chat

  const [prevChats, setPrevChats] = useState([]);
  // 📖 Messages array: [{role: "user"|"assistant", content: "..."}]
  // Loaded from backend when switching threads
  // Appended when sending/receiving messages

  const [newChat, setNewChat] = useState(true);
  // 📖 Is this a new (empty) conversation?
  // Shows "Start a New Chat!" message when true

  const [allThreads, setAllThreads] = useState([]);
  // 📖 All threads for sidebar: [{threadId, title}, ...]
  // Fetched from backend on load

  const [theme, setTheme] = useState(() => {
    // 📖 Lazy initialization: Only runs on first render
    // 📌 WHY FUNCTION? Avoids localStorage call on every re-render
    if (typeof window === "undefined") return "dark";
    // 📖 SSR guard: window doesn't exist on server
    return localStorage.getItem("theme") || "dark";
    // 📖 Persist theme preference in localStorage
  });

  // 🆕 USER ID for isolation (unique per browser)
  const [userId, setUserId] = useState(() => {
    // 📖 Generate unique user_id per browser session
    // 📌 WHY? Each user gets their own chat history and global memory
    if (typeof window === "undefined") return "default";
    let storedUserId = localStorage.getItem("sigma_gpt_user_id");
    if (!storedUserId) {
      // Generate new user_id if doesn't exist
      storedUserId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem("sigma_gpt_user_id", storedUserId);
    }
    return storedUserId;
  });


  // ===========================================================================
  // EFFECTS (Side Effects)
  // ===========================================================================
  
  useEffect(() => {
    // 📖 Apply theme to document when it changes
    document.documentElement.setAttribute("data-theme", theme);
    document.body.setAttribute("data-theme", theme);
    // 📌 data-theme attribute used by CSS: [data-theme="dark"] {...}
    
    localStorage.setItem("theme", theme);
    // 📖 Persist to localStorage for next visit
  }, [theme]);
  // 📌 Dependency array [theme]: Only runs when theme changes


  // ===========================================================================
  // CONTEXT VALUE
  // 📖 All values provided to child components via Context
  // ===========================================================================
  
  const providerValues = {
    prompt, setPrompt,
    reply, setReply,
    currThreadId, setCurrThreadId,
    newChat, setNewChat,
    prevChats, setPrevChats,
    allThreads, setAllThreads,
    theme, setTheme,
    userId  // 🆕 User ID for isolation (unique per browser)
  };
  // 📖 All state and setters bundled for Context
  // 📌 Any child component can access these via useContext(MyContext)


  // ===========================================================================
  // RENDER
  // ===========================================================================
  
  return (
    <div className={`app theme-${theme}`}>
      {/* 📖 Root div with theme class for styling */}
      
      <MyContext.Provider value={providerValues}>
        {/* 📖 Context Provider: Makes state available to all children */}
        {/* 📌 value={providerValues} is what useContext returns */}
        
        <Sidebar />
        {/* 📖 Left sidebar: Chat history, new chat button, settings */}
        
        <main className="mainShell">
          {/* 📖 Main content area */}
          
          <Routes>
            {/* 📖 React Router: Renders component based on URL */}
            
            <Route path="/" element={<ChatWindow />} />
            {/* 📖 Home route: Main chat interface */}
            
            <Route path="/features" element={<Features />} />
            {/* 📖 Features page */}
            
            <Route path="/plans" element={<Plans />} />
            {/* 📖 Plans/pricing page */}
            
            <Route path="*" element={<Navigate to="/" replace />} />
            {/* 📖 Catch-all: Redirect unknown routes to home */}
            {/* 📌 replace: Don't add to browser history */}
          </Routes>
        </main>
      </MyContext.Provider>
    </div>
  )
}

export default App


// =============================================================================
//                         SUMMARY FOR INTERVIEWS
// =============================================================================
/**
 * 📌 REACT CONCEPTS USED:
 * 
 * 1. FUNCTIONAL COMPONENTS:
 *    - Modern React pattern
 *    - Cleaner than class components
 *    - Use hooks for state/effects
 * 
 * 2. HOOKS:
 *    - useState: State management
 *    - useEffect: Side effects
 *    - useContext: (in children) Read context
 * 
 * 3. CONTEXT PATTERN:
 *    - Create context (MyContext.jsx)
 *    - Provide value (App.jsx Provider)
 *    - Consume (children use useContext)
 * 
 * 4. REACT ROUTER:
 *    - Client-side routing
 *    - No page reload on navigation
 *    - Route component renders based on URL
 * 
 * 5. LAZY STATE INITIALIZATION:
 *    - useState(() => ...) for expensive init
 *    - Used for localStorage read
 * 
 * 📌 ARCHITECTURE:
 *    App (state, context, routing)
 *      └── Sidebar (navigation)
 *      └── ChatWindow (main feature)
 */
