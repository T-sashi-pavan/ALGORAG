"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { 
  FileText, Send, Sparkles, AlertTriangle, Shield, Layers, RefreshCw, 
  BookOpen, Trash2, ArrowLeft, Pin, PinOff, Plus, Search, Edit2, Check, X, 
  Paperclip, FileImage, FileCode, CheckCircle, HelpCircle
} from "lucide-react"
import InfinityLogo from "@/components/InfinityLogo"
import ParticleBackground from "@/components/ParticleBackground"
import axios from "axios"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

interface Message {
  role: string
  content: string
  confidence_score?: number
  citations?: any[]
  grounded?: boolean
  timestamp?: string
}

interface ChatSession {
  session_id: string
  _id?: string
  title: string
  pinned: boolean
  document_ids: string[]
  created_at: string
  updated_at: string
}

interface UploadChip {
  id: string
  name: string
  progress: number
  status: "Uploading" | "Indexing" | "Indexed" | "Error"
  document_id?: string
  page_count?: number
}

export default function Dashboard() {
  // Session State
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionSearch, setSessionSearch] = useState("")
  
  // Renaming State
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState("")

  // Documents Index State
  const [documents, setDocuments] = useState<any[]>([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  
  // Chat message & loading state
  const [inputMessage, setInputMessage] = useState("")
  const [sending, setSending] = useState(false)
  const [activeCitation, setActiveCitation] = useState<any | null>(null)

  // Floating attachment chips
  const [uploadingChips, setUploadingChips] = useState<UploadChip[]>([])
  const [isDragging, setIsDragging] = useState(false)

  const chatEndRef = useRef<HTMLDivElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  // Fetch document directory list from backend
  const fetchDocuments = async () => {
    setLoadingDocs(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/api/upload/documents`)
      setDocuments(response.data.documents || [])
    } catch (error) {
      console.error("Failed to load documents:", error)
    } finally {
      setLoadingDocs(false)
    }
  }

  // Fetch all chat sessions
  const fetchSessions = async (selectFirst = false) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/chat/sessions`)
      const fetchedSessions = response.data.sessions || []
      setSessions(fetchedSessions)
      
      // Local Storage Restoration Fallback
      let storedSessionId = localStorage.getItem("active_session_id")
      
      if (fetchedSessions.length > 0) {
        if (selectFirst || !storedSessionId || !fetchedSessions.find((s: any) => s.session_id === storedSessionId)) {
          const firstSessionId = fetchedSessions[0].session_id
          setCurrentSessionId(firstSessionId)
          localStorage.setItem("active_session_id", firstSessionId)
          fetchMessages(firstSessionId)
        } else {
          setCurrentSessionId(storedSessionId)
          fetchMessages(storedSessionId)
        }
      } else {
        // No sessions exist: create one automatically
        handleCreateSession("General Discussion")
      }
    } catch (error) {
      console.error("Failed to fetch sessions:", error)
    }
  }

  // Fetch messages inside an active session
  const fetchMessages = async (sessionId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/chat/sessions/${sessionId}/messages`)
      const fetchedMessages = response.data.messages || []
      
      if (fetchedMessages.length === 0) {
        setMessages([
          {
            role: "assistant",
            content: "Hello! I am your grounded document intelligence assistant. Ask me anything about your uploaded documents. I will strictly answer from context with zero hallucinations.",
            confidence_score: 1.0,
            citations: [],
            grounded: true
          }
        ])
      } else {
        setMessages(fetchedMessages)
      }
    } catch (error) {
      console.error(`Failed to load messages for session ${sessionId}:`, error)
    }
  }

  // Create a new session
  const handleCreateSession = async (titleStr = "New Conversation") => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat/sessions`, {
        title: titleStr,
        document_ids: []
      })
      const newSession = response.data.data
      setSessions((prev) => [newSession, ...prev])
      setCurrentSessionId(newSession.session_id)
      localStorage.setItem("active_session_id", newSession.session_id)
      setMessages([
        {
          role: "assistant",
          content: "Hello! I am your grounded document intelligence assistant. Ask me anything about your uploaded documents. I will strictly answer from context with zero hallucinations.",
          confidence_score: 1.0,
          citations: [],
          grounded: true
        }
      ])
    } catch (error) {
      console.error("Failed to create chat session:", error)
    }
  }

  // Rename session
  const handleRenameSession = async (sessionId: string) => {
    if (!editingTitle.trim()) return
    try {
      await axios.put(`${API_BASE_URL}/api/chat/sessions/${sessionId}`, {
        title: editingTitle
      })
      setSessions((prev) =>
        prev.map((s) => (s.session_id === sessionId ? { ...s, title: editingTitle } : s))
      )
      setEditingSessionId(null)
    } catch (error) {
      console.error("Failed to rename session:", error)
    }
  }

  // Toggle Pin session
  const handleTogglePinSession = async (session: ChatSession) => {
    try {
      const updatedPin = !session.pinned
      await axios.put(`${API_BASE_URL}/api/chat/sessions/${session.session_id}`, {
        pinned: updatedPin
      })
      setSessions((prev) =>
        prev
          .map((s) => (s.session_id === session.session_id ? { ...s, pinned: updatedPin } : s))
          .sort((a, b) => Number(b.pinned) - Number(a.pinned))
      )
    } catch (error) {
      console.error("Failed to toggle pin state:", error)
    }
  }

  // Delete session
  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm("Are you sure you want to delete this chat session?")) return
    try {
      await axios.delete(`${API_BASE_URL}/api/chat/sessions/${sessionId}`)
      const remainingSessions = sessions.filter((s) => s.session_id !== sessionId)
      setSessions(remainingSessions)
      
      if (currentSessionId === sessionId) {
        if (remainingSessions.length > 0) {
          const nextSessionId = remainingSessions[0].session_id
          setCurrentSessionId(nextSessionId)
          localStorage.setItem("active_session_id", nextSessionId)
          fetchMessages(nextSessionId)
        } else {
          handleCreateSession("General Discussion")
        }
      }
    } catch (error) {
      console.error("Failed to delete session:", error)
    }
  }

  // File drag and drop listeners
  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const onDragLeave = () => {
    setIsDragging(false)
  }

  // File upload logic inside dashboard
  const handleUploadFiles = async (files: FileList) => {
    if (files.length === 0) return
    setIsDragging(false)

    Array.from(files).forEach(async (file) => {
      const chipId = Math.random().toString(36).substring(7)
      
      // Insert initial uploading chip
      const newChip: UploadChip = {
        id: chipId,
        name: file.name,
        progress: 15,
        status: "Uploading"
      }
      setUploadingChips((prev) => [...prev, newChip])

      const formData = new FormData()
      formData.append("files", file)

      try {
        // Upload file
        const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (progressEvent) => {
            const percentage = Math.round((progressEvent.loaded * 100) / (progressEvent.total || progressEvent.loaded))
            setUploadingChips((prev) =>
              prev.map((c) => (c.id === chipId ? { ...c, progress: Math.min(percentage, 80) } : c))
            )
          }
        })

        // File uploaded successfully, now background indexing begins
        setUploadingChips((prev) =>
          prev.map((c) => (c.id === chipId ? { ...c, progress: 90, status: "Indexing" } : c))
        )

        const uploadedFile = response.data.data[0]
        const docId = uploadedFile.document_id

        // Polling loop to wait for file status to be "Indexed" in backend
        let indexed = false
        let retries = 0
        while (!indexed && retries < 15) {
          await new Promise((r) => setTimeout(r, 2000))
          try {
            const docList = await axios.get(`${API_BASE_URL}/api/upload/documents`)
            const docInfo = docList.data.documents.find((d: any) => d.document_id === docId)
            if (docInfo && docInfo.status === "Indexed") {
              indexed = true
              setUploadingChips((prev) =>
                prev.map((c) =>
                  c.id === chipId
                    ? {
                        ...c,
                        progress: 100,
                        status: "Indexed",
                        document_id: docId,
                        page_count: docInfo.page_count
                      }
                    : c
                )
              )
              fetchDocuments()

              // Auto-attach document to current active session scope
              if (currentSessionId) {
                const currentSession = sessions.find((s) => s.session_id === currentSessionId)
                if (currentSession) {
                  const updatedDocs = [...(currentSession.document_ids || []), docId]
                  await axios.put(`${API_BASE_URL}/api/chat/sessions/${currentSessionId}`, {
                    document_ids: updatedDocs
                  })
                  setSessions((prev) =>
                    prev.map((s) => (s.session_id === currentSessionId ? { ...s, document_ids: updatedDocs } : s))
                  )
                }
              }
            }
          } catch (pollingErr) {
            console.error("Polling document status failed:", pollingErr)
          }
          retries++
        }

        if (!indexed) {
          setUploadingChips((prev) =>
            prev.map((c) => (c.id === chipId ? { ...c, status: "Error" } : c))
          )
        }

      } catch (error) {
        console.error("Dashboard upload failed:", error)
        setUploadingChips((prev) =>
          prev.map((c) => (c.id === chipId ? { ...c, status: "Error" } : c))
        )
      }
    })
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (e.dataTransfer.files) {
      handleUploadFiles(e.dataTransfer.files)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleUploadFiles(e.target.files)
    }
  }

  // Remove a document chip or delete document
  const handleRemoveChip = async (chip: UploadChip) => {
    // Delete uploading chip from state
    setUploadingChips((prev) => prev.filter((c) => c.id !== chip.id))
    
    // Detach from active session if present
    if (chip.document_id && currentSessionId) {
      const currentSession = sessions.find((s) => s.session_id === currentSessionId)
      if (currentSession) {
        const updatedDocs = (currentSession.document_ids || []).filter((id) => id !== chip.document_id)
        await axios.put(`${API_BASE_URL}/api/chat/sessions/${currentSessionId}`, {
          document_ids: updatedDocs
        })
        setSessions((prev) =>
          prev.map((s) => (s.session_id === currentSessionId ? { ...s, document_ids: updatedDocs } : s))
        )
      }
    }
  }

  // Toggle active document selection inside the sidebar
  const toggleDocSelection = async (docId: string) => {
    if (!currentSessionId) return
    const currentSession = sessions.find((s) => s.session_id === currentSessionId)
    if (!currentSession) return

    let updatedDocs = []
    if (currentSession.document_ids.includes(docId)) {
      updatedDocs = currentSession.document_ids.filter((id) => id !== docId)
    } else {
      updatedDocs = [...currentSession.document_ids, docId]
    }

    try {
      await axios.put(`${API_BASE_URL}/api/chat/sessions/${currentSessionId}`, {
        document_ids: updatedDocs
      })
      setSessions((prev) =>
        prev.map((s) => (s.session_id === currentSessionId ? { ...s, document_ids: updatedDocs } : s))
      )
    } catch (error) {
      console.error("Failed to update active documents scope for session:", error)
    }
  }

  // Delete an indexed file completely from vector store
  const handleDeleteDoc = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm("Are you sure you want to remove this document completely from the RAG Index?")) return
    try {
      await axios.delete(`${API_BASE_URL}/api/upload/documents/${docId}`)
      setDocuments((prev) => prev.filter((d) => d.document_id !== docId))
      
      // Update all sessions to remove references
      setSessions((prev) =>
        prev.map((s) => ({
          ...s,
          document_ids: (s.document_ids || []).filter((id) => id !== docId)
        }))
      )
      
      // Remove chip if visible
      setUploadingChips((prev) => prev.filter((c) => c.document_id !== docId))
    } catch (error) {
      console.error("Failed to delete document:", error)
    }
  }

  // Send message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputMessage.trim() || sending || !currentSessionId) return

    const userText = inputMessage
    setInputMessage("")
    setSending(true)

    // Prepend user message bubble
    const userMsg: Message = { role: "user", content: userText }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)

    // Get active scope document IDs
    const activeSession = sessions.find((s) => s.session_id === currentSessionId)
    const docIds = activeSession?.document_ids || []

    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat`, {
        messages: nextMessages.map((m) => ({ role: m.role, content: m.content })),
        document_ids: docIds.length > 0 ? docIds : null,
        similarity_threshold: 0.40,
        session_id: currentSessionId
      })
      
      // Update messages thread from response
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.data.answer,
          confidence_score: response.data.confidence_score,
          citations: response.data.citations || [],
          grounded: response.data.grounded
        }
      ])
    } catch (error) {
      console.error("Chat communication failure:", error)
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "System connection loss. Please verify that your backend service is running and configured.",
          confidence_score: 0.0,
          citations: [],
          grounded: false
        }
      ])
    } finally {
      setSending(false)
    }
  }

  // Bootstrapping fetches
  useEffect(() => {
    fetchDocuments()
    fetchSessions()
  }, [])

  // Auto-scroll chat feed
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, sending])

  // Get active session object
  const activeSessionObj = sessions.find((s) => s.session_id === currentSessionId)
  
  // Filter sessions based on search
  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(sessionSearch.toLowerCase())
  )

  // Helper to check file extension and render icon
  const getFileIcon = (name: string) => {
    const ext = name.split(".").pop()?.toLowerCase()
    if (ext === "pdf") return <FileText className="w-4 h-4 text-red-400" />
    if (["png", "jpg", "jpeg", "bmp", "gif"].includes(ext || "")) return <FileImage className="w-4 h-4 text-green-400" />
    if (["txt", "doc", "docx", "pptx"].includes(ext || "")) return <FileCode className="w-4 h-4 text-cyber-blue" />
    return <FileText className="w-4 h-4 text-cyber-gray" />
  }

  return (
    <main 
      onDragOver={onDragOver}
      onDrop={onDrop}
      className="relative min-h-screen flex flex-col bg-cyber-bg bg-grid-mesh overflow-hidden z-10 select-none"
    >
      <ParticleBackground />

      {/* Drag & Drop Visual Overlay Screen */}
      <AnimatePresence>
        {isDragging && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onDragLeave={onDragLeave}
            className="fixed inset-0 bg-cyber-bg/95 border-4 border-dashed border-cyber-purple/60 backdrop-blur-md z-50 flex flex-col items-center justify-center pointer-events-none"
          >
            <Sparkles className="w-20 h-20 text-cyber-purple animate-bounce mb-6" />
            <h2 className="text-2xl md:text-3xl font-display font-black text-white tracking-widest uppercase">
              DRAG & DROP SHARD DETECTED
            </h2>
            <p className="text-sm text-cyber-gray mt-2">
              Release files to instantly analyze, index, and attach into current session workspace
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 flex max-w-7xl mx-auto w-full px-4 py-4 relative z-20 h-screen overflow-hidden">
        
        {/* LEFT COLUMN: Premium Stacked Sidebar (Chats + Documents) */}
        <aside className="hidden lg:flex flex-col w-[320px] min-h-0 mr-4 space-y-4">
          
          {/* Section A: Chat Session Manager */}
          <section className="flex-[3] flex flex-col min-h-0 cyber-glass rounded-xl border border-white/5 p-4 overflow-hidden">
            
            {/* Header + Add button */}
            <div className="flex items-center justify-between mb-4 flex-shrink-0">
              <div className="flex items-center gap-2">
                <InfinityLogo size={24} />
                <h2 className="font-display font-bold text-xs tracking-wider text-white uppercase">
                  CONVERSATIONS
                </h2>
              </div>
              <button
                onClick={() => handleCreateSession()}
                className="p-1.5 hover:bg-white/5 rounded-lg text-cyber-purple border border-cyber-purple/20 hover:border-cyber-purple transition-all"
                title="New Conversation"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Search sessions */}
            <div className="relative mb-3 flex-shrink-0">
              <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-cyber-gray/60" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={sessionSearch}
                onChange={(e) => setSessionSearch(e.target.value)}
                className="w-full bg-cyber-dark/80 pl-8 pr-3 py-1.8 rounded-lg border border-white/5 text-[11px] text-white placeholder-cyber-gray/40 focus:outline-none focus:border-cyber-purple transition-all"
              />
            </div>

            {/* Sessions Chronological List */}
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
              {filteredSessions.length === 0 ? (
                <div className="text-center py-6 text-[10px] text-cyber-gray/60">
                  No sessions found
                </div>
              ) : (
                filteredSessions.map((session) => {
                  const isActive = session.session_id === currentSessionId
                  const isPinned = session.pinned
                  const isEditing = editingSessionId === session.session_id

                  return (
                    <div
                      key={session.session_id}
                      onClick={() => {
                        if (!isEditing) {
                          setCurrentSessionId(session.session_id)
                          localStorage.setItem("active_session_id", session.session_id)
                          fetchMessages(session.session_id)
                        }
                      }}
                      className={`p-2.5 rounded-lg border text-left cursor-pointer transition-all flex items-center justify-between group ${
                        isActive
                          ? "bg-cyber-purple/10 border-cyber-purple/40 shadow-neon-glass text-white"
                          : "bg-cyber-dark/40 border-white/5 hover:border-cyber-purple/20 text-cyber-gray hover:text-white"
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <FileText className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? "text-cyber-purple" : "text-cyber-gray"}`} />
                        
                        {isEditing ? (
                          <input
                            type="text"
                            value={editingTitle}
                            onChange={(e) => setEditingTitle(e.target.value)}
                            onBlur={() => handleRenameSession(session.session_id)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleRenameSession(session.session_id)
                            }}
                            className="bg-cyber-dark text-[11px] text-white px-1.5 py-0.5 rounded border border-cyber-purple focus:outline-none w-full"
                            autoFocus
                          />
                        ) : (
                          <span className="text-[11px] font-medium truncate pr-1">
                            {session.title}
                          </span>
                        )}
                      </div>

                      {/* Hover action settings */}
                      {!isEditing && (
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setEditingSessionId(session.session_id)
                              setEditingTitle(session.title)
                            }}
                            className="p-1 hover:bg-white/5 rounded text-cyber-gray hover:text-white"
                            title="Rename"
                          >
                            <Edit2 className="w-3 h-3" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleTogglePinSession(session)
                            }}
                            className={`p-1 hover:bg-white/5 rounded ${isPinned ? "text-cyber-purple" : "text-cyber-gray hover:text-white"}`}
                            title={isPinned ? "Unpin" : "Pin"}
                          >
                            <Pin className="w-3 h-3" />
                          </button>
                          <button
                            onClick={(e) => handleDeleteSession(session.session_id, e)}
                            className="p-1 hover:bg-white/5 rounded text-cyber-gray hover:text-red-400"
                            title="Delete"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      )}

                      {/* Display small pin indicator if pinned but not hovering */}
                      {isPinned && !isEditing && (
                        <Pin className="w-2.5 h-2.5 text-cyber-purple group-hover:hidden flex-shrink-0 ml-1" />
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </section>

          {/* Section B: Document Scope Selector (Workspace Files Context) */}
          <section className="flex-[2] flex flex-col min-h-0 cyber-glass rounded-xl border border-white/5 p-4 overflow-hidden">
            <div className="flex items-center justify-between mb-3 flex-shrink-0">
              <h2 className="font-display font-bold text-xs tracking-wider text-white uppercase flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-cyber-blue" />
                CONTEXT SOURCES
              </h2>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="text-[10px] text-cyber-blue hover:underline font-mono"
              >
                + Add Files
              </button>
              <input
                type="file"
                multiple
                ref={fileInputRef}
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>

            <p className="text-[9px] text-cyber-gray/70 leading-normal mb-3 flex-shrink-0">
              Check files to restrict context scopes. Uncheck all to query the entire indexed vector space.
            </p>

            {/* Document checkbox grid */}
            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {loadingDocs && documents.length === 0 ? (
                <div className="text-center py-6 text-[10px] text-cyber-gray animate-pulse">
                  Syncing document indexes...
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center py-8 text-[10px] text-cyber-gray/60 border border-dashed border-white/5 rounded-lg">
                  No documents in workspace.
                </div>
              ) : (
                documents.map((doc) => {
                  const isChecked = activeSessionObj?.document_ids?.includes(doc.document_id) || false
                  
                  return (
                    <div
                      key={doc.document_id}
                      onClick={() => toggleDocSelection(doc.document_id)}
                      className={`p-2 rounded-lg border text-left cursor-pointer transition-all flex items-start justify-between gap-2 ${
                        isChecked
                          ? "bg-cyber-blue/5 border-cyber-blue/30 text-white"
                          : "bg-cyber-dark/40 border-white/5 hover:border-cyber-blue/15 text-cyber-gray hover:text-white"
                      }`}
                    >
                      <div className="flex items-start gap-2 min-w-0">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}} // Controlled by outer div click
                          className="mt-0.5 rounded border-white/10 accent-cyber-blue text-cyber-bg focus:ring-0 cursor-pointer"
                        />
                        <div className="min-w-0">
                          <h4 className="text-[11px] font-semibold truncate pr-1">{doc.filename}</h4>
                          <span className="text-[9px] text-cyber-gray/60 block mt-0.5">
                            {doc.chunk_count} blocks • {doc.page_count || 1} pgs
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={(e) => handleDeleteDoc(doc.document_id, e)}
                        className="text-cyber-gray/50 hover:text-red-400 p-0.5 rounded hover:bg-white/5 flex-shrink-0"
                        title="Remove completely"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )
                })
              )}
            </div>
          </section>
        </aside>

        {/* RIGHT COLUMN: Immersive Conversational RAG Workspace */}
        <section className="flex-1 flex flex-col min-h-0 cyber-glass rounded-xl border border-white/5 overflow-hidden">
          
          {/* Chat Panel Header - Active Scope indicator */}
          <header className="px-4 py-3 border-b border-white/5 bg-cyber-dark/30 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-3">
              <button
                onClick={() => window.location.href = "/"}
                className="p-1.5 hover:bg-white/5 rounded-lg text-cyber-gray hover:text-white transition-all lg:hidden"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <div>
                <h3 className="text-xs font-bold text-white tracking-wider truncate max-w-[200px] md:max-w-md">
                  {activeSessionObj ? activeSessionObj.title : "Workspace chat"}
                </h3>
                <p className="text-[9px] text-cyber-gray mt-0.5 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  Scope: {(activeSessionObj?.document_ids?.length || 0) > 0 
                    ? `${activeSessionObj?.document_ids?.length} attached document(s)` 
                    : "Universal context search"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-1.5 text-cyber-purple px-2 py-0.8 rounded bg-cyber-purple/5 border border-cyber-purple/20 text-[10px]">
                <Shield className="w-3.5 h-3.5" />
                <span>Grounded Guard Active</span>
              </div>
              <button
                onClick={() => {
                  fetchDocuments()
                  if (currentSessionId) fetchMessages(currentSessionId)
                }}
                className="p-1.5 hover:bg-white/5 rounded-lg text-cyber-gray hover:text-white transition-all"
                title="Sync Workspace"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          </header>
          
          {/* Scrollable chat transcripts feed */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 pr-2">
            {messages.map((msg, idx) => {
              const isAI = msg.role === "assistant"
              return (
                <div 
                  key={idx} 
                  className={`flex flex-col ${isAI ? "items-start" : "items-end"}`}
                >
                  {/* Speaker indicator */}
                  <div className="flex items-center gap-2 mb-1 text-[10px] text-cyber-gray/70 px-1 font-mono uppercase">
                    <span>{isAI ? "ALGONOX INTELLIGENCE" : "OPERATOR"}</span>
                    {isAI && msg.confidence_score !== undefined && (
                      <span className={`px-1.5 py-0.2 rounded border font-semibold ${
                        msg.confidence_score > 0.7
                          ? "bg-green-500/10 border-green-500/30 text-green-400"
                          : msg.confidence_score > 0.4
                          ? "bg-yellow-500/10 border-yellow-500/30 text-yellow-400"
                          : "bg-red-500/10 border-red-500/30 text-red-400"
                      }`}>
                        Conf: {Math.round(msg.confidence_score * 100)}%
                      </span>
                    )}
                  </div>

                  {/* Chat bubble */}
                  <div className={`p-4 rounded-2xl max-w-xl text-xs leading-relaxed ${
                    isAI
                      ? msg.grounded
                        ? "cyber-glass border border-white/5 text-slate-100"
                        : "bg-cyber-dark border border-red-500/20 text-red-100 shadow-neon-glass"
                      : "bg-gradient-to-r from-cyber-purple/20 to-cyber-indigo/20 border border-cyber-purple/35 text-white"
                  }`}>
                    {msg.content}

                    {/* Grounded ref warning indicator */}
                    {isAI && !msg.grounded && (
                      <div className="mt-3 flex items-center gap-2 text-[10px] text-red-400 bg-red-500/10 px-3 py-2 rounded-lg border border-red-500/20">
                        <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                        <span>Hallucination prevention filter activated. Answer falls below grounded reference threshold.</span>
                      </div>
                    )}

                    {/* Citations block */}
                    {isAI && msg.citations && msg.citations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-white/5 text-left">
                        <div className="flex items-center gap-1.5 text-[9px] text-cyber-blue font-bold uppercase mb-2 tracking-wide font-mono">
                          <BookOpen className="w-3 h-3" />
                          Grounded References ({msg.citations.length})
                        </div>
                        
                        <div className="flex flex-wrap gap-1.5">
                          {msg.citations.map((cit: any, cIdx: number) => (
                            <button
                              key={cIdx}
                              onClick={() => setActiveCitation(cit)}
                              className="text-[9px] px-2 py-0.8 rounded bg-cyber-blue/10 border border-cyber-blue/20 hover:border-cyber-blue hover:text-white text-cyber-blue transition-all"
                            >
                              {cit.filename} (Pg {cit.page_number || 1})
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
            
            {/* Thinking typist loader loop */}
            {sending && (
              <div className="flex flex-col items-start">
                <div className="text-[10px] text-cyber-gray/70 mb-1 px-1 font-mono uppercase">ALGONOX THINKING...</div>
                <div className="cyber-glass px-4 py-3 rounded-2xl border border-cyber-blue/20 text-xs text-cyber-blue/80 flex items-center gap-2 animate-pulse shadow-neon-blue">
                  <Sparkles className="w-4 h-4 animate-spin" />
                  <span>Synthesizing multi-layered document outline contexts...</span>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Chat entry form footer with integrated float upload bar */}
          <footer className="border-t border-white/5 bg-cyber-dark/50 p-4">
            
            {/* Floating Attachment Tray (ChatGPT style chips bar) */}
            <AnimatePresence>
              {uploadingChips.length > 0 && (
                <motion.div 
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="flex flex-wrap gap-2 mb-3 pb-3 border-b border-white/5 items-center overflow-hidden"
                >
                  {uploadingChips.map((chip) => {
                    const isUploading = chip.status === "Uploading"
                    const isIndexing = chip.status === "Indexing"
                    const isIndexed = chip.status === "Indexed"
                    const isError = chip.status === "Error"

                    return (
                      <motion.div
                        key={chip.id}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        className={`flex items-center gap-2 bg-cyber-bg/90 border rounded-lg px-2.5 py-1.5 text-[10px] shadow-lg max-w-[200px] ${
                          isError 
                            ? "border-red-500/30 text-red-300" 
                            : isIndexed 
                            ? "border-cyber-purple/30 text-white" 
                            : "border-cyber-blue/20 text-cyber-blue"
                        }`}
                      >
                        {getFileIcon(chip.name)}
                        <span className="truncate flex-1 font-medium">{chip.name}</span>
                        
                        {/* Status elements */}
                        {isUploading && (
                          <span className="text-[8px] animate-pulse font-mono">
                            {chip.progress}%
                          </span>
                        )}
                        {isIndexing && (
                          <span className="text-[8px] text-cyber-purple animate-pulse font-mono font-bold">
                            INDEXING
                          </span>
                        )}
                        {isIndexed && (
                          <span className="text-[8px] text-green-400 font-mono flex items-center gap-0.5">
                            <CheckCircle className="w-2.5 h-2.5" />
                            {chip.page_count ? `${chip.page_count}p` : "OK"}
                          </span>
                        )}
                        
                        <button
                          type="button"
                          onClick={() => handleRemoveChip(chip)}
                          className="text-cyber-gray hover:text-white p-0.5 rounded"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </motion.div>
                    )
                  })}
                </motion.div>
              )}
            </AnimatePresence>

            <form onSubmit={handleSendMessage} className="flex gap-2 items-center">
              
              {/* File Paperclip trigger button inside chat input */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="p-3 bg-cyber-dark/80 border border-white/10 rounded-xl hover:border-cyber-blue text-cyber-gray hover:text-white transition-all flex items-center justify-center flex-shrink-0"
                title="Attach document (PDF, DOCX, PPTX, Image)"
              >
                <Paperclip className="w-4 h-4" />
              </button>

              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask grounded questions about your documents (e.g., summarize this file, compare revenue)..."
                disabled={sending}
                className="flex-1 bg-cyber-bg px-4 py-3 rounded-xl border border-white/10 text-xs text-white placeholder-cyber-gray/40 focus:outline-none focus:border-cyber-purple transition-all"
              />
              
              <button
                type="submit"
                disabled={sending || !inputMessage.trim()}
                className="bg-cyber-purple hover:bg-cyber-purple/80 text-white font-bold p-3 rounded-xl transition-all shadow-neon-purple disabled:opacity-50 disabled:shadow-none flex items-center justify-center"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </footer>
        </section>
      </div>

      {/* Citations Drawer Popup Modal (NotebookLM-like overlay card) */}
      <AnimatePresence>
        {activeCitation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setActiveCitation(null)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95, y: 15 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 15 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-2xl cyber-glass p-6 rounded-2xl border border-cyber-blue/30 shadow-neon-blue text-left"
            >
              <div className="flex justify-between items-start mb-4 pb-3 border-b border-white/5">
                <div>
                  <span className="text-[8px] px-2 py-0.5 bg-cyber-blue/15 border border-cyber-blue/30 text-cyber-blue rounded font-bold uppercase font-mono tracking-wider">
                    Page {activeCitation.page_number || 1} Grounded Source
                  </span>
                  <h3 className="text-xs font-bold text-white mt-1.5">{activeCitation.filename}</h3>
                </div>
                <button
                  onClick={() => setActiveCitation(null)}
                  className="text-cyber-gray hover:text-white text-xs p-1 hover:bg-white/5 rounded transition-all"
                >
                  Close
                </button>
              </div>

              <div className="bg-cyber-dark/80 p-4 rounded-xl border border-white/5 text-[11px] leading-relaxed text-slate-300 max-h-80 overflow-y-auto font-mono whitespace-pre-wrap">
                {activeCitation.text}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  )
}

