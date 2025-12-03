// =============================================================================
//                     CONFIG.JS - API Configuration
// =============================================================================
/**
 * 📚 WHAT IS THIS FILE?
 * ---------------------
 * Centralized configuration for API endpoints.
 * 
 * 📌 ENVIRONMENT VARIABLES:
 * ------------------------
 * In Vite, environment variables must be prefixed with VITE_
 * 
 * Development: Uses .env file (VITE_API_URL=http://localhost:8080)
 * Production: Set in Vercel dashboard (VITE_API_URL=https://your-backend.onrender.com)
 * 
 * 📌 USAGE:
 * --------
 * import { API_URL } from './config';
 * fetch(`${API_URL}/api/chat`, ...)
 */

// Get API URL from environment variable, fallback to localhost for development
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8080";

export { API_URL };

