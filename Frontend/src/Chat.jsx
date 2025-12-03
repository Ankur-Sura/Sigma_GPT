// =============================================================================
//                     CHAT.JSX - Message Display Component
// =============================================================================
/**
 * 📚 WHAT IS THIS FILE?
 * ---------------------
 * Displays the chat messages (user and assistant) with animations.
 * 
 * 📌 FEATURES:
 * ------------
 * 1. Shows "Start a New Chat!" for empty conversations
 * 2. Renders messages with different styles for user/assistant
 * 3. Word-by-word typing animation for new AI responses
 * 4. Markdown rendering with syntax highlighting
 * 5. Auto-scroll to bottom for new messages
 * 
 * 📌 INTERVIEW TIP:
 * -----------------
 * "The Chat component renders messages with markdown support and a typing
 *  animation for AI responses. It automatically scrolls to show new messages."
 */

import "./Chat.css";
// 📖 Component-specific styles

import React, { useContext, useState, useEffect, useRef } from "react";
// 📖 React hooks:
// - useContext: Access global state
// - useState: Local animation state
// - useEffect: Run animation effect
// - useRef: Track previous message count and scroll container

import { MyContext } from "./MyContext";
// 📖 Global state context

import ReactMarkdown from "react-markdown";
// 📖 Renders markdown as React components

import rehypeHighlight from "rehype-highlight";
// 📖 Syntax highlighting for code blocks

import remarkGfm from "remark-gfm";
// 📖 GitHub Flavored Markdown support (tables, strikethrough)

import "highlight.js/styles/github-dark.css";
// 📖 Code highlighting theme


function Chat() {
    // =========================================================================
    // CONTEXT & STATE
    // =========================================================================
    
    const {
        newChat, 
        prevChats,
        currThreadId
    } = useContext(MyContext);
    // 📖 newChat: Is this a new conversation?
    // 📖 prevChats: Array of messages [{role, content}, ...]

    const [animatedReply, setAnimatedReply] = useState(null);
    // 📖 Current state of typing animation
    // null = no animation, "" = starting, "word..." = in progress

    const prevCountRef = useRef(0);
    // 📖 Tracks previous message count to detect new messages

    const chatContainerRef = useRef(null);
    // 📖 Reference to the scrollable chat container

    const isInitialLoadRef = useRef(true);
    // 📖 Track if this is the first load of messages for a thread


    // =========================================================================
    // TYPING ANIMATION EFFECT
    // =========================================================================
    /**
     * 📌 HOW THE ANIMATION WORKS:
     * 
     * 1. Detect new assistant message (prevChats length increased)
     * 2. Split response into words
     * 3. Use setInterval to add words one by one
     * 4. Clear interval when done
     */

    useEffect(() => {
        if(!prevChats?.length) {
            setAnimatedReply(null);
            return;
        }

        const last = prevChats[prevChats.length - 1];
        const prevCount = prevCountRef.current;
        prevCountRef.current = prevChats.length;

        // Skip animation when loading old threads (not a new message)
        if(isInitialLoadRef.current) {
            setAnimatedReply(null);
            return;
        }

        // Only animate new assistant messages
        if(prevChats.length <= prevCount || last.role !== "assistant") {
            setAnimatedReply(null);
            return;
        }

        // Start word-by-word animation
        const words = last.content.split(" ");
        let idx = 0;
        setAnimatedReply("");
        
        // Scroll to bottom for new messages
        if (chatContainerRef.current) {
            chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
        
        const interval = setInterval(() => {
            setAnimatedReply(words.slice(0, idx + 1).join(" "));
            idx++;
            if(idx >= words.length) clearInterval(interval);
            
            // Keep scrolled to bottom during animation
            if (chatContainerRef.current) {
                chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
            }
        }, 40);
        // 📖 40ms = ~25 words per second

        return () => clearInterval(interval);
    }, [prevChats]);


    // =========================================================================
    // SCROLL TO BOTTOM ON INITIAL LOAD
    // =========================================================================
    
    useEffect(() => {
        if (prevChats?.length > 0 && chatContainerRef.current) {
            if (isInitialLoadRef.current) {
                // Initial load - scroll to bottom to show newest messages
                const container = chatContainerRef.current;
                container.scrollTop = container.scrollHeight;
                isInitialLoadRef.current = false;
            }
        }
    }, [prevChats]);


    // =========================================================================
    // RESET FLAG WHEN THREAD CHANGES
    // =========================================================================
    
    useEffect(() => {
        isInitialLoadRef.current = true;
    }, [currThreadId]);


    // =========================================================================
    // RENDER
    // =========================================================================
    
    return (
        <>
            {newChat && <h1>Start a New Chat!</h1>}
            
            <div className="chats" ref={chatContainerRef}>
                {
                    prevChats?.map((chat, idx) => {
                        const isLast = idx === prevChats.length - 1;
                        const showAnimated = isLast && chat.role === "assistant" && animatedReply !== null;
                        const contentToShow = showAnimated ? animatedReply : chat.content;
                        const isUploadMsg = chat.content?.startsWith("📄");
                        
                        const containerClass = chat.role === "user"
                            ? "userDiv"
                            : `gptDiv ${isUploadMsg ? "boxMessage" : ""}`;
                        
                        return (
                        <div className={containerClass} key={idx}>
                            {
                                chat.role === "user"? 
                                <p className="userMessage">{contentToShow}</p> : 
                                <div className="assistantMessage">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                                        {contentToShow}
                                    </ReactMarkdown>
                                </div>
                            }
                        </div>);
                    })
                }
            </div>
        </>
    )
}

export default Chat;


// =============================================================================
//                         SUMMARY FOR INTERVIEWS
// =============================================================================
/**
 * 📌 REACT CONCEPTS USED:
 * 
 * 1. CONDITIONAL RENDERING:
 *    - {newChat && <h1>...</h1>}
 *    - Shows welcome only when newChat is true
 * 
 * 2. LIST RENDERING:
 *    - map() to render array of messages
 *    - key prop for React reconciliation
 * 
 * 3. useRef:
 *    - Persist value without re-render
 *    - Track previous state for comparison
 *    - Reference DOM elements
 * 
 * 4. ANIMATION WITH useEffect + setInterval:
 *    - Start interval on new message
 *    - Update state progressively
 *    - Cleanup on unmount
 * 
 * 5. THIRD-PARTY LIBRARIES:
 *    - ReactMarkdown: Markdown to React
 *    - rehype-highlight: Syntax highlighting
 *    - remark-gfm: GitHub Flavored Markdown
 */
