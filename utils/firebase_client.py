"""Firebase Firestore client for Lumiere Dashboard"""

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional
import json


def get_firestore_client() -> Optional[firestore.Client]:
    """
    Initialize and return Firestore client using Streamlit secrets.
    Uses singleton pattern to avoid re-initialization.
    Connects to the 'production' database.
    """
    try:
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            # Build credentials dict from secrets
            firebase_config = dict(st.secrets["firebase"])
            
            # Handle private key newlines (common issue with secrets)
            if "private_key" in firebase_config:
                firebase_config["private_key"] = firebase_config["private_key"].replace(
                    "\\n", "\n"
                )
            
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
        
        # Connect to the 'production' database (not the default)
        return firestore.client(database_id="production")
    
    except KeyError as e:
        st.error(f"⚠️ Firebase configuration missing: {e}")
        st.info("Please configure Firebase credentials in `.streamlit/secrets.toml`")
        return None
    except Exception as e:
        st.error(f"⚠️ Failed to initialize Firebase: {e}")
        return None


@st.cache_data(ttl=30, show_spinner=False)
def fetch_sessions(_db: firestore.Client) -> list[dict]:
    """
    Fetch all sessions from Firestore.
    
    Args:
        _db: Firestore client (underscore prefix prevents caching issues)
    
    Returns:
        List of session documents as dictionaries
    """
    if _db is None:
        return []
    
    try:
        sessions_ref = _db.collection("sessions")
        docs = sessions_ref.stream()
        
        sessions = []
        for doc in docs:
            session_data = doc.to_dict()
            session_data["_doc_id"] = doc.id
            sessions.append(session_data)
        
        return sessions
    
    except Exception as e:
        st.error(f"⚠️ Failed to fetch sessions: {e}")
        return []


def clear_session_cache():
    """Clear the cached session data to force refresh"""
    fetch_sessions.clear()


def fetch_session_by_id(_db: firestore.Client, session_id: str) -> Optional[dict]:
    """
    Fetch a single session by its session_id field.
    
    Args:
        _db: Firestore client
        session_id: The session_id to look up
    
    Returns:
        Session document as dictionary, or None if not found
    """
    if _db is None or not session_id:
        return None
    
    try:
        sessions_ref = _db.collection("sessions")
        query = sessions_ref.where("session_id", "==", session_id).limit(1)
        docs = list(query.stream())
        
        if docs:
            session_data = docs[0].to_dict()
            session_data["_doc_id"] = docs[0].id
            return session_data
        return None
    
    except Exception as e:
        st.error(f"⚠️ Failed to fetch session: {e}")
        return None


def firestore_timestamp_to_datetime(ts: dict) -> Optional[float]:
    """
    Convert Firestore timestamp dict to Unix timestamp.
    
    Args:
        ts: Dict with '_seconds' and '_nanoseconds' keys
    
    Returns:
        Unix timestamp as float, or None if invalid
    """
    if ts is None:
        return None
    
    if isinstance(ts, dict):
        seconds = ts.get("_seconds", ts.get("seconds", 0))
        nanoseconds = ts.get("_nanoseconds", ts.get("nanoseconds", 0))
        return seconds + nanoseconds / 1e9
    
    # Handle native Firestore timestamp objects
    if hasattr(ts, "timestamp"):
        return ts.timestamp()
    
    return None
