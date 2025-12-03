// =============================================================================
//                     REACT CONTEXT - Global State Management
// =============================================================================
/**
 * 📚 WHAT IS THIS FILE?
 * ---------------------
 * Creates a React Context for sharing state across all components.
 * 
 * 📌 WHAT IS CONTEXT?
 * -------------------
 * Context = A way to pass data through the component tree without props
 * 
 * WITHOUT CONTEXT (Prop Drilling):
 *     App → Sidebar → ThreadList → ThreadItem → needs "currThreadId"
 *     Every component must pass the prop down!
 * 
 * WITH CONTEXT:
 *     App (Provider) → any component can access "currThreadId" directly
 * 
 * 📌 WHEN TO USE CONTEXT:
 * -----------------------
 * - Theme (dark/light mode)
 * - User authentication
 * - Current language
 * - Global app state (like this chat app)
 * 
 * 📌 INTERVIEW TIP:
 * -----------------
 * "I use React Context for global state that many components need access to,
 *  like the current thread ID, chat history, and theme. This avoids prop
 *  drilling and keeps components clean."
 * 
 * 🔗 CONTEXT FLOW:
 * ----------------
 *     MyContext.jsx (creates context)
 *           ↓
 *     App.jsx (provides values via Provider)
 *           ↓
 *     Any component (consumes via useContext hook)
 * 
 * 📌 STATE IN THIS APP:
 * ---------------------
 * - prompt: Current input text
 * - reply: Last AI response
 * - currThreadId: Active conversation ID
 * - prevChats: Messages in current thread
 * - allThreads: All threads for sidebar
 * - theme: "dark" or "light"
 */

import { createContext } from "react";
// 📖 createContext: React function to create a context object
// Returns: { Provider, Consumer } (we use Provider in App.jsx)

export const MyContext = createContext("");
// 📖 Creates the context with default value ""
// 📌 Default value used if component reads context without Provider above it
// 
// 📌 USAGE:
// In App.jsx:
//     <MyContext.Provider value={{prompt, setPrompt, ...}}>
//       <ChildComponents />
//     </MyContext.Provider>
// 
// In any child component:
//     const { prompt, setPrompt } = useContext(MyContext);


// =============================================================================
//                         SUMMARY FOR INTERVIEWS
// =============================================================================
/**
 * 📌 REACT CONTEXT CONCEPTS:
 * 
 * 1. PROVIDER:
 *    - Wraps component tree
 *    - Passes value to all children
 *    - <MyContext.Provider value={...}>
 * 
 * 2. CONSUMER (useContext):
 *    - Hook to read context value
 *    - const value = useContext(MyContext)
 *    - Re-renders when value changes
 * 
 * 3. ALTERNATIVES:
 *    - Redux: More complex, better for large apps
 *    - Zustand: Simpler, less boilerplate
 *    - Jotai/Recoil: Atomic state management
 *    - Context: Built-in, good for medium apps
 * 
 * 📌 WHY I CHOSE CONTEXT:
 * - Built into React (no extra dependency)
 * - Simple for this app's needs
 * - Easy to understand and explain
 */