// =============================================================================
//                     SIDEBAR.JSX - Navigation & Chat History
// =============================================================================
/**
 * 📚 WHAT IS THIS FILE?
 * ---------------------
 * The sidebar component showing:
 * 1. Logo and "New Chat" button
 * 2. Chat history (all threads)
 * 3. Settings dropdown (theme, features, plans)
 * 
 * 📌 FEATURES:
 * ------------
 * - Create new chat (generates UUID, clears state)
 * - Switch between chats (loads messages from backend)
 * - Delete chats
 * - Rename chats
 * - Toggle theme (dark/light)
 * - Navigate to Features/Plans pages
 * 
 * 📌 INTERVIEW TIP:
 * -----------------
 * "The Sidebar manages chat navigation. It fetches thread list from the
 *  backend, handles CRUD operations on threads, and provides theme toggling
 *  with localStorage persistence."
 */

import "./Sidebar.css";
// 📖 Component-specific styles

import { useContext, useEffect, useState } from "react";
// 📖 React hooks:
// - useContext: Access global state
// - useEffect: Fetch data on mount
// - useState: Local UI state (dropdown open/closed)

import { MyContext } from "./MyContext.jsx";
// 📖 Global state context

import {v1 as uuidv1} from "uuid";
// 📖 Generate unique IDs for new chats

import { useNavigate } from "react-router-dom";
// 📖 Programmatic navigation (no <Link> needed)

import { API_URL } from "./config.js";
// 📖 API base URL from environment variable


function Sidebar() {
    // =========================================================================
    // CONTEXT & STATE
    // =========================================================================
    
    const {
        allThreads, setAllThreads, 
        currThreadId, setCurrThreadId,
        setNewChat, setPrompt, setReply, setPrevChats, 
        theme, setTheme
    } = useContext(MyContext);
    // 📖 Destructure all needed state from context
    
    const [aboutOpen, setAboutOpen] = useState(false);
    // 📖 Local state: Is settings dropdown open?

    const navigate = useNavigate();
    // 📖 React Router hook for navigation

    // =========================================================================
    // HELPER FUNCTIONS
    // =========================================================================

    const capitalizeTitle = (title = "") => {
        // 📖 Capitalize first letter of thread title
        if (!title) return "Untitled";
        return title.charAt(0).toUpperCase() + title.slice(1);
    };


    // =========================================================================
    // API FUNCTIONS
    // =========================================================================
    /**
     * 📌 API CALLS IN THIS COMPONENT:
     * 
     * GET /api/thread          → Fetch all threads (getAllThreads)
     * GET /api/thread/:id      → Fetch messages (changeThread)
     * DELETE /api/thread/:id   → Delete thread (deleteThread)
     * PATCH /api/thread/:id    → Rename thread (inline in JSX)
     */

    const getAllThreads = async () => {
        // 📖 Fetch all chat threads from backend
        try {
            const response = await fetch(`${API_URL}/api/thread`);
            const res = await response.json();
            
            const filteredData = res
                .filter(thread => thread.threadId !== "global-shared")
                // 📖 Hide internal global memory thread from UI
                .map(thread => ({threadId: thread.threadId, title: capitalizeTitle(thread.title)}));
            
            setAllThreads(filteredData);
        } catch(err) {
            console.log(err);
        }
    };

    useEffect(() => {
        getAllThreads();
    }, [currThreadId])
    // 📖 Re-fetch threads when current thread changes

    useEffect(() => {
        getAllThreads();
    }, [])
    // 📖 Fetch on component mount


    // =========================================================================
    // THREAD MANAGEMENT
    // =========================================================================

    const createNewChat = () => {
        // 📖 Create a new chat conversation
        setNewChat(true);
        setPrompt("");
        setReply(null);
        setCurrThreadId(uuidv1());
        setPrevChats([]);
        navigate("/");
    }

    const changeThread = async (newThreadId) => {
        // 📖 Switch to a different chat thread
        setCurrThreadId(newThreadId);

        try {
            // Fetch ALL messages for this thread (simple, no pagination)
            const response = await fetch(`${API_URL}/api/thread/${newThreadId}`);
            const res = await response.json();
            
            // Handle both formats: array (old) or object with messages (new)
            const messages = Array.isArray(res) ? res : (res.messages || []);
            
            setPrevChats(messages);
            setNewChat(false);
            setReply(null);
            navigate("/");
            
        } catch(err) {
            console.log("Error loading thread:", err);
        }
    }   

    const deleteThread = async (threadId) => {
        // 📖 Delete a chat thread
        try {
            const response = await fetch(`${API_URL}/api/thread/${threadId}`, {method: "DELETE"});
            const res = await response.json();
            console.log(res);

            // Update UI immediately (optimistic update)
            setAllThreads(prev => prev.filter(thread => thread.threadId !== threadId));

            if(threadId === currThreadId) {
                createNewChat();
            }

        } catch(err) {
            console.log(err);
        }
    }

    return (
        <section className="sidebar">
            <button onClick={createNewChat}>
                <div className="brand">
                    <img src="src/assets/blacklogo.png" alt="gpt logo" className="logo"></img>
                    <span className="brand-text">Sigma GPT</span>
                </div>
                <span><i className="fa-solid fa-pen-to-square"></i></span>
            </button>


            <ul className="history">
                {
                    allThreads?.map((thread, idx) => {
                        const displayTitle = capitalizeTitle(thread.title);
                        return (
                        <li key={idx} 
                            onClick={(e) => changeThread(thread.threadId)}
                            className={thread.threadId === currThreadId ? "highlighted": " "}
                        >
                            <span className="historyTitle">
                                {displayTitle?.length > 40 ? `${displayTitle.slice(0, 40)}…` : displayTitle}
                            </span>
                            <i className="fa-solid fa-trash"
                                onClick={(e) => {
                                    e.stopPropagation();
                                deleteThread(thread.threadId);
                                }}
                            ></i>
                            <i className="fa-solid fa-pen edit-icon"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    const newName = prompt("Rename chat", thread.title || "Untitled");
                                    if(!newName) return;
                                    fetch(`${API_URL}/api/thread/${thread.threadId}`, {
                                        method: "PATCH",
                                        headers: {"Content-Type": "application/json"},
                                        body: JSON.stringify({title: newName})
                                    })
                                    .then(res => res.json())
                                    .then(() => {
                                        setAllThreads(prev => prev.map(t => t.threadId === thread.threadId ? {...t, title: capitalizeTitle(newName)} : t));
                                    })
                                    .catch(err => console.log(err));
                                }}
                            ></i>
                        </li>
                        );
                    })
                }
            </ul>
            <div className="sign profileRow" onClick={() => setAboutOpen(prev => !prev)}>
                <div className="avatar">A</div>
                <div className="profileInfo">
                    <span className="profileName">Ankur</span>
                </div>
            </div>
            {
                aboutOpen && (
                    <div className="aboutDropdown">
                        <div className="aboutHeader">
                            <span>Settings</span>
                            <span className="aboutByline">By Ankur Sura</span>
                        </div>
                        <div className="aboutItem">
                            <div className="themeCopy">
                                <span className="label">Theme</span>
                                <span className="sub">{theme === "dark" ? "Black" : "Light"}</span>
                            </div>
                            <label className="toggleSwitch" title="Toggle theme">
                                <input type="checkbox" checked={theme === "dark"} onChange={() => setTheme(prev => prev === "dark" ? "light" : "dark")} />
                                <span className="sliderSwitch"></span>
                            </label>
                        </div>
                        <div className="aboutItem linkItem" onClick={() => {navigate("/features"); setAboutOpen(false);}}>
                            <i className="fa-solid fa-circle-info"></i> Features
                        </div>
                        <div className="aboutItem linkItem" onClick={() => {navigate("/plans"); setAboutOpen(false);}}>
                            <i className="fa-solid fa-cloud-arrow-up"></i> Upgrade plan
                        </div>
                    </div>
                )
            }
        </section>
    )
}

export default Sidebar;


// =============================================================================
//                         SUMMARY FOR INTERVIEWS
// =============================================================================
/**
 * 📌 REACT CONCEPTS USED:
 * 
 * 1. API CALLS WITH fetch:
 *    - GET: Fetch threads/messages
 *    - DELETE: Remove threads
 *    - PATCH: Rename threads
 * 
 * 2. OPTIMISTIC UPDATES:
 *    - Update UI immediately, don't wait for server
 *    - Better user experience
 *    - Example: setAllThreads(prev => prev.filter(...))
 * 
 * 3. EVENT HANDLING:
 *    - onClick for buttons
 *    - e.stopPropagation() to prevent bubbling
 *    - Inline handlers for simple operations
 * 
 * 4. CONDITIONAL RENDERING:
 *    - {aboutOpen && <div>...</div>}
 *    - Shows settings only when open
 * 
 * 5. PROGRAMMATIC NAVIGATION:
 *    - useNavigate() hook
 *    - navigate("/path") instead of <Link>
 */
