"use client"

import React, { useState, useCallback, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { 
  Search, FileText, ArrowRight, ShieldCheck, Sparkles, Network, Terminal, 
  ChevronDown, ChevronUp, Check, Mail, Eye, ExternalLink, HelpCircle, 
  Sliders, Calendar, Globe, AlertTriangle, RefreshCw, Clock, X, Star
} from "lucide-react"
import InfinityLogo from "@/components/InfinityLogo"
import ParticleBackground from "@/components/ParticleBackground"
import axios from "axios"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

interface PriorityDoc {
  document_id: string
  priority_rank: number
  filename: string
  portal: string
  relevance_score: number
  published_date: string
  ai_summary: string
  keywords_matched: string[]
  confidence_score: number
  why_selected: string
  url: string
  status: string
  semantic_similarity: number
  keyword_match: number
  recency: number
  source_quality: number
  document_completeness: number
  final_score: number
}

interface EmailLog {
  delivery_id: string
  recipient: string
  subject: string
  sent_at: string
  status: string
  filenames: string[]
}

export default function Home() {
  const [keyword, setKeyword] = useState("")
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<any[]>([])
  
  // New AI Document Priority Center States
  const [priorityDocs, setPriorityDocs] = useState<PriorityDoc[]>([])
  const [ranking, setRanking] = useState(false)
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const [previewDoc, setPreviewDoc] = useState<PriorityDoc | null>(null)
  
  // Table Interactions
  const [sortField, setSortField] = useState<"final_score" | "published_date" | "priority_rank">("final_score")
  const [sortAsc, setSortAsc] = useState(false)
  const [filterPortal, setFilterPortal] = useState("All")
  const [minScore, setMinScore] = useState(0)
  const [tableSearch, setTableSearch] = useState("")
  const [expandedSummaryId, setExpandedSummaryId] = useState<string | null>(null)
  
  // Email Modal States
  const [emailModalOpen, setEmailModalOpen] = useState(false)
  const [emailDraftLoading, setEmailDraftLoading] = useState(false)
  const [emailSubject, setEmailSubject] = useState("")
  const [emailBody, setEmailBody] = useState("")
  const [recipientEmail, setRecipientEmail] = useState("sessi111111@gmail.com")
  const [customMessage, setCustomMessage] = useState("")
  const [sendingEmail, setSendingEmail] = useState(false)
  
  // Logs & Notifications
  const [emailLogs, setEmailLogs] = useState<EmailLog[]>([])
  const [notification, setNotification] = useState<{message: string, type: "success" | "info" | "error"} | null>(null)

  // Fetch recent email logs
  const fetchEmailLogs = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/priority/email-logs`)
      setEmailLogs(response.data.logs || [])
    } catch (error) {
      console.error("Failed to load email logs:", error)
    }
  }

  useEffect(() => {
    fetchEmailLogs()
  }, [])

  // Auto-clear notification after 4s
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 4000)
      return () => clearTimeout(timer)
    }
  }, [notification])

  // Handle portal searches & priority ranking calculations
  const handlePortalSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!keyword.trim()) return
    
    setSearching(true)
    setRanking(true)
    setSearchResults([])
    setPriorityDocs([])
    setSelectedDocIds([])
    setPreviewDoc(null)

    try {
      // 1. Trigger concurrent public portal search
      const searchRes = await axios.post(`${API_BASE_URL}/api/search`, { keyword })
      setSearchResults(searchRes.data)
      setSearching(false)

      // 2. Fetch mathematically calculated Priority rankings
      const priorityRes = await axios.post(`${API_BASE_URL}/api/priority/rank`, { keyword })
      setPriorityDocs(priorityRes.data)
    } catch (error) {
      console.error("Ingestion pipelines failed:", error)
      setNotification({
        message: "Pipeline connection failed. Please ensure the FastAPI backend is running.",
        type: "error"
      })
      setSearching(false)
    } finally {
      setRanking(false)
    }
  }

  // Handle document checkbox selections
  const toggleDocSelection = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((dId) => dId !== id) : [...prev, id]
    )
  }

  const toggleSelectAll = () => {
    if (selectedDocIds.length === filteredDocs.length) {
      setSelectedDocIds([])
    } else {
      setSelectedDocIds(filteredDocs.map((d) => d.document_id))
    }
  }

  // Manual Rank Override Control
  const handleRankOverride = async (index: number, direction: "up" | "down") => {
    const newDocs = [...priorityDocs]
    const targetIdx = direction === "up" ? index - 1 : index + 1
    
    if (targetIdx < 0 || targetIdx >= newDocs.length) return
    
    // Swap document rank positions
    const temp = newDocs[index]
    newDocs[index] = newDocs[targetIdx]
    newDocs[targetIdx] = temp
    
    // Recalculate rank values
    const updatedDocs = newDocs.map((d, i) => ({
      ...d,
      priority_rank: i + 1
    }))
    
    setPriorityDocs(updatedDocs)
    setNotification({
      message: `Manual Override Applied: "${temp.filename}" rank updated to #${targetIdx + 1}.`,
      type: "info"
    })

    // Log this review triage action in MongoDB
    try {
      await axios.post(`${API_BASE_URL}/api/priority/review-action`, {
        document_id: temp.document_id,
        action_type: "override_rank",
        metadata: {
          original_rank: index + 1,
          new_rank: targetIdx + 1
        }
      })
    } catch (err) {
      console.error("Failed to log override action:", err)
    }
  }

  // Trigger Send to HR Email Wizard
  const handleSendToHRTrigger = async () => {
    if (selectedDocIds.length === 0) return
    
    setEmailModalOpen(true)
    setEmailDraftLoading(true)
    setEmailSubject("")
    setEmailBody("")

    try {
      const response = await axios.post(`${API_BASE_URL}/api/priority/generate-email`, {
        document_ids: selectedDocIds,
        keyword: keyword
      })
      setEmailSubject(response.data.subject)
      setEmailBody(response.data.body)
    } catch (error) {
      console.error("Failed to generate AI email draft:", error)
      setNotification({
        message: "Failed to generate email draft. Check your server logs.",
        type: "error"
      })
    } finally {
      setEmailDraftLoading(false)
    }
  }

  // Dispatch Email Send
  const handleConfirmSendEmail = async () => {
    setSendingEmail(true)
    try {
      const res = await axios.post(`${API_BASE_URL}/api/priority/send-email`, {
        document_ids: selectedDocIds,
        recipient_email: recipientEmail,
        subject: emailSubject,
        body: emailBody,
        custom_message: customMessage
      })

      setNotification({
        message: `Email queued successfully (Delivery ID: ${res.data.delivery_id}).`,
        type: "success"
      })
      setEmailModalOpen(false)
      setSelectedDocIds([])
      setCustomMessage("")
      
      // Auto refresh logs after short wait
      setTimeout(() => fetchEmailLogs(), 3000)
    } catch (error) {
      console.error("Failed to send HR email:", error)
      setNotification({
        message: "Email delivery initiation failed.",
        type: "error"
      })
    } finally {
      setSendingEmail(false)
    }
  }

  // Helper for sorting
  const sortedDocs = [...priorityDocs].sort((a, b) => {
    let aVal: any = a[sortField]
    let bVal: any = b[sortField]
    
    if (sortField === "published_date") {
      // Default extraction of years for coarse sorting
      const aYr = parseInt(a.published_date.match(/\d{4}/)?.[0] || "0")
      const bYr = parseInt(b.published_date.match(/\d{4}/)?.[0] || "0")
      return sortAsc ? aYr - bYr : bYr - aYr
    }
    
    return sortAsc 
      ? (aVal > bVal ? 1 : -1) 
      : (aVal < bVal ? 1 : -1)
  })

  // Filter docs
  const filteredDocs = sortedDocs.filter((doc) => {
    const matchesPortal = filterPortal === "All" || doc.portal === filterPortal
    const matchesScore = doc.relevance_score >= minScore
    const matchesSearch = doc.filename.toLowerCase().includes(tableSearch.toLowerCase()) || 
                          doc.portal.toLowerCase().includes(tableSearch.toLowerCase())
    return matchesPortal && matchesScore && matchesSearch
  })

  const uniquePortals = ["All", ...Array.from(new Set(priorityDocs.map((d) => d.portal)))]

  // Visual Priority Badge mapper
  const getPriorityBadge = (score: number) => {
    if (score >= 80) {
      return <span className="px-2.5 py-0.5 rounded bg-green-500/10 border border-green-500/30 text-green-400 text-[10px] font-bold shadow-[0_0_10px_rgba(34,197,94,0.1)]">HIGH PRIORITY</span>
    } else if (score >= 60) {
      return <span className="px-2.5 py-0.5 rounded bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-[10px] font-bold">MODERATE</span>
    } else {
      return <span className="px-2.5 py-0.5 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-[10px] font-bold">LOW FIT</span>
    }
  }

  return (
    <main className="relative min-h-screen flex flex-col justify-between overflow-x-hidden bg-cyber-bg bg-grid-mesh pb-12 z-10 select-none">
      <ParticleBackground />

      {/* Floating Notifications Toast */}
      <AnimatePresence>
        {notification && (
          <motion.div
            initial={{ opacity: 0, y: -50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -50, scale: 0.9 }}
            className={`fixed top-6 right-6 z-50 px-5 py-3 rounded-xl border shadow-2xl backdrop-blur-md text-xs font-semibold flex items-center gap-3 ${
              notification.type === "success" 
                ? "bg-green-500/10 border-green-500/30 text-green-400 shadow-[0_0_20px_rgba(34,197,94,0.15)]"
                : notification.type === "error"
                ? "bg-red-500/10 border-red-500/30 text-red-400 shadow-[0_0_20px_rgba(239,68,68,0.15)]"
                : "bg-cyber-blue/10 border-cyber-blue/30 text-cyber-blue shadow-[0_0_20px_rgba(0,240,255,0.15)]"
            }`}
          >
            <Sparkles className="w-4 h-4 animate-spin" />
            <span>{notification.message}</span>
            <button onClick={() => setNotification(null)} className="text-gray-400 hover:text-white ml-2">
              <X className="w-3.5 h-3.5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header Panel */}
      <header className="w-full max-w-7xl mx-auto px-6 py-6 flex items-center justify-between relative z-20">
        <div className="flex items-center gap-3">
          <InfinityLogo size={42} />
          <span className="font-display font-extrabold text-lg tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-cyber-purple text-glow-blue">
            ALGONOX RAG
          </span>
        </div>
        <button
          onClick={() => window.location.href = "/dashboard"}
          className="cyber-glass px-5 py-2 rounded-lg border border-cyber-purple/20 text-xs font-semibold text-cyber-purple hover:border-cyber-purple hover:text-white transition-all shadow-neon-glass duration-300"
        >
          ENTER WORKSPACE
        </button>
      </header>

      {/* Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-4 max-w-7xl mx-auto w-full pt-6">
        
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2 }}
          className="mb-6"
        >
          <InfinityLogo size={120} />
        </motion.div>

        <h1 className="text-3xl md:text-5xl font-display font-black tracking-tight text-white mb-4">
          MULTIMODAL DOCUMENT <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue via-cyber-indigo to-cyber-purple text-glow-blue">
            INTELLIGENCE DASHBOARD
          </span>
        </h1>

        <p className="text-xs md:text-sm text-cyber-gray max-w-xl mb-8 leading-relaxed">
          Concurrent multi-portal search scraping engine equipped with mathematically precise weighted priority ranking and one-click HR mail routing.
        </p>

        {/* Unified Search Form */}
        <div className="w-full max-w-2xl cyber-glass p-4 rounded-xl border border-cyber-blue/10 mb-8">
          <form onSubmit={handlePortalSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3.5 w-4 h-4 text-cyber-gray" />
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="Search across 8 portals (e.g. LLM fine-tuning, quantum encryption)..."
                className="w-full bg-cyber-dark/80 pl-9 pr-4 py-3 rounded-lg border border-cyber-blue/20 text-xs text-white placeholder-cyber-gray/70 focus:outline-none focus:border-cyber-blue transition-all"
              />
            </div>
            <button
              type="submit"
              disabled={searching}
              className="bg-cyber-blue hover:bg-cyber-blue/80 text-cyber-bg font-bold px-6 py-3 rounded-lg text-xs transition-all shadow-neon-blue flex items-center gap-1.5"
            >
              {searching ? "SCRAPING..." : "SEARCH"}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>

        {/* Loading Spinner for Priority center ranking calculation */}
        {ranking && (
          <div className="w-full max-w-4xl py-12 flex flex-col items-center justify-center">
            <RefreshCw className="w-12 h-12 text-cyber-purple animate-spin mb-4" />
            <h3 className="font-display font-bold text-sm text-white tracking-widest uppercase">
              CALIBRATING MULTI-LAYERED PRIORITY INGESTION RANKS...
            </h3>
            <p className="text-[10px] text-cyber-gray mt-2 animate-pulse">
              Computing keyword match density, recency decay factor, and semantic relevance scores.
            </p>
          </div>
        )}

        {/* AI DOCUMENT PRIORITY CENTER SECTION */}
        {priorityDocs.length > 0 && !ranking && (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-7xl text-left mt-6 bg-cyber-dark/40 border border-cyber-purple/10 rounded-2xl p-6 relative z-20 shadow-2xl backdrop-blur-sm"
          >
            {/* Header section with selected status */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-cyber-purple/20 pb-4 mb-6 gap-4">
              <div>
                <h2 className="font-display font-black text-white tracking-widest text-sm flex items-center gap-2">
                  <Star className="w-4.5 h-4.5 text-cyber-purple animate-pulse" />
                  AI DOCUMENT PRIORITY CENTER
                </h2>
                <p className="text-[10px] text-cyber-gray mt-1 leading-normal">
                  Documents prioritized automatically using the 5-Factor mathematical relevance formula.
                </p>
              </div>

              {selectedDocIds.length > 0 && (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex items-center gap-3 bg-cyber-purple/10 border border-cyber-purple/35 rounded-xl p-2"
                >
                  <span className="text-[10px] font-bold text-cyber-purple pl-1 uppercase font-mono">
                    {selectedDocIds.length} Document(s) Selected
                  </span>
                  <button
                    onClick={handleSendToHRTrigger}
                    className="bg-cyber-purple hover:bg-cyber-purple/80 text-white font-bold px-4 py-2 rounded-lg text-[10px] shadow-neon-purple flex items-center gap-1.5 transition-all"
                  >
                    <Mail className="w-3.5 h-3.5" />
                    SEND TO HR TEAM
                  </button>
                </motion.div>
              )}
            </div>

            {/* Sort, Filter & Table Search Toolbar */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-cyber-gray/60" />
                <input
                  type="text"
                  placeholder="Filter Priority Documents..."
                  value={tableSearch}
                  onChange={(e) => setTableSearch(e.target.value)}
                  className="w-full bg-cyber-bg pl-8 pr-3 py-1.8 rounded-lg border border-white/5 text-[10px] text-white focus:outline-none focus:border-cyber-purple transition-all"
                />
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[9px] text-cyber-gray font-mono uppercase">Portal:</span>
                <select
                  value={filterPortal}
                  onChange={(e) => setFilterPortal(e.target.value)}
                  className="bg-cyber-bg border border-white/5 text-[10px] text-white rounded-lg p-1.5 focus:outline-none flex-1"
                >
                  {uniquePortals.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-[9px] text-cyber-gray font-mono uppercase">Min Score:</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={minScore}
                  onChange={(e) => setMinScore(parseInt(e.target.value))}
                  className="accent-cyber-purple flex-1"
                />
                <span className="text-[10px] text-white font-bold w-6 text-right">{minScore}%</span>
              </div>

              <div className="flex gap-2 justify-end items-center">
                <span className="text-[9px] text-cyber-gray font-mono uppercase">Sort by:</span>
                <div className="flex rounded-lg overflow-hidden border border-white/5 text-[9px]">
                  <button
                    onClick={() => { setSortField("final_score"); setSortAsc(!sortAsc); }}
                    className={`px-2.5 py-1.5 font-bold ${sortField === "final_score" ? "bg-cyber-purple/20 text-white" : "bg-cyber-bg text-cyber-gray"}`}
                  >
                    Relevance
                  </button>
                  <button
                    onClick={() => { setSortField("published_date"); setSortAsc(!sortAsc); }}
                    className={`px-2.5 py-1.5 font-bold border-l border-white/5 ${sortField === "published_date" ? "bg-cyber-purple/20 text-white" : "bg-cyber-bg text-cyber-gray"}`}
                  >
                    Date
                  </button>
                </div>
              </div>
            </div>

            {/* Priority Table Container */}
            <div className="overflow-x-auto w-full border border-white/5 rounded-xl bg-cyber-dark/80">
              <table className="w-full text-left text-[11px] border-collapse min-w-[1000px]">
                <thead>
                  <tr className="bg-cyber-bg border-b border-white/5 text-[9px] text-cyber-gray tracking-wider uppercase font-mono">
                    <th className="p-3.5 text-center w-14">Rank</th>
                    <th className="p-3.5 w-10 text-center">
                      <input
                        type="checkbox"
                        checked={selectedDocIds.length === filteredDocs.length && filteredDocs.length > 0}
                        onChange={toggleSelectAll}
                        className="rounded border-white/10 accent-cyber-purple text-cyber-bg cursor-pointer focus:ring-0"
                      />
                    </th>
                    <th className="p-3.5 w-[250px]">Document Info</th>
                    <th className="p-3.5">Portal</th>
                    <th className="p-3.5">Score</th>
                    <th className="p-3.5">Relevance Status</th>
                    <th className="p-3.5">Keywords</th>
                    <th className="p-3.5">Confidence</th>
                    <th className="p-3.5 text-center w-[160px]">Triage Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocs.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="p-8 text-center text-[10px] text-cyber-gray/50">
                        No priority documents match current search or filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredDocs.map((doc, index) => {
                      const isSelected = selectedDocIds.includes(doc.document_id)
                      const isExpanded = expandedSummaryId === doc.document_id

                      return (
                        <React.Fragment key={doc.document_id}>
                          <tr className={`border-b border-white/5 transition-colors hover:bg-white/[0.02] ${isSelected ? "bg-cyber-purple/5" : ""}`}>
                            
                            {/* Priority Rank Override Controls */}
                            <td className="p-3.5 text-center">
                              <div className="flex flex-col items-center justify-center gap-0.5">
                                <button
                                  onClick={() => handleRankOverride(index, "up")}
                                  disabled={index === 0}
                                  className="text-cyber-gray hover:text-cyber-purple disabled:opacity-20 transition-all"
                                  title="Promote Priority Rank"
                                >
                                  <ChevronUp className="w-3.5 h-3.5" />
                                </button>
                                <span className="font-display font-extrabold text-[12px] text-white text-glow-purple">
                                  #{doc.priority_rank}
                                </span>
                                <button
                                  onClick={() => handleRankOverride(index, "down")}
                                  disabled={index === filteredDocs.length - 1}
                                  className="text-cyber-gray hover:text-cyber-purple disabled:opacity-20 transition-all"
                                  title="Demote Priority Rank"
                                >
                                  <ChevronDown className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </td>

                            {/* Checkbox Selector */}
                            <td className="p-3.5 text-center">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleDocSelection(doc.document_id)}
                                className="rounded border-white/10 accent-cyber-purple text-cyber-bg cursor-pointer focus:ring-0"
                              />
                            </td>

                            {/* Document Info */}
                            <td className="p-3.5">
                              <div className="flex flex-col min-w-0 pr-2">
                                <span className="font-bold text-slate-100 truncate hover:text-cyber-blue cursor-pointer" onClick={() => setPreviewDoc(doc)}>
                                  {doc.filename}
                                </span>
                                <span className="text-[9px] text-cyber-gray mt-1 block">
                                  Published: {doc.published_date}
                                </span>
                              </div>
                            </td>

                            {/* Portal */}
                            <td className="p-3.5 font-semibold text-slate-300">
                              {doc.portal}
                            </td>

                            {/* Weighted Final Score */}
                            <td className="p-3.5">
                              <span className="font-display font-extrabold text-[12px] text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-cyber-purple text-glow-blue">
                                {doc.relevance_score}%
                              </span>
                            </td>

                            {/* Visual Priority Badges */}
                            <td className="p-3.5">
                              {getPriorityBadge(doc.relevance_score)}
                            </td>

                            {/* Match Keywords Chips */}
                            <td className="p-3.5">
                              <div className="flex flex-wrap gap-1 max-w-[150px]">
                                {doc.keywords_matched.slice(0, 3).map((kw, kwIdx) => (
                                  <span key={kwIdx} className="px-1.5 py-0.5 rounded bg-cyber-blue/5 border border-cyber-blue/15 text-[8px] text-cyber-blue uppercase font-mono">
                                    {kw}
                                  </span>
                                ))}
                                {doc.keywords_matched.length > 3 && (
                                  <span className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[8px] text-cyber-gray font-mono">
                                    +{doc.keywords_matched.length - 3}
                                  </span>
                                )}
                              </div>
                            </td>

                            {/* Vector similarity confidence */}
                            <td className="p-3.5 font-mono text-[10px] text-cyber-gray">
                              {doc.confidence_score}%
                            </td>

                            {/* Triage Actions */}
                            <td className="p-3.5 text-center">
                              <div className="flex items-center justify-center gap-1.5">
                                <button
                                  onClick={() => setPreviewDoc(doc)}
                                  className="p-1.5 hover:bg-white/5 rounded-lg text-cyber-blue border border-cyber-blue/10 hover:border-cyber-blue transition-all"
                                  title="Inspect Document details & scores"
                                >
                                  <Eye className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => {
                                    setExpandedSummaryId(isExpanded ? null : doc.document_id)
                                  }}
                                  className="p-1.5 hover:bg-white/5 rounded-lg text-cyber-gray hover:text-white border border-white/5 hover:border-white/10 transition-all text-[9px] font-bold"
                                >
                                  {isExpanded ? "HIDE" : "AI SUMMARY"}
                                </button>
                                {doc.url ? (
                                  <a
                                    href={doc.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="p-1.5 hover:bg-white/5 rounded-lg text-cyber-purple border border-cyber-purple/10 hover:border-cyber-purple transition-all inline-block"
                                    title="Open Original source PDF"
                                  >
                                    <ExternalLink className="w-3.5 h-3.5" />
                                  </a>
                                ) : (
                                  <span className="text-red-400 font-bold text-[8px]">OFFLINE</span>
                                )}
                              </div>
                            </td>
                          </tr>

                          {/* Expandable AI Summary Card */}
                          <AnimatePresence>
                            {isExpanded && (
                              <tr>
                                <td colSpan={9} className="p-4 bg-cyber-dark/40 border-b border-white/5">
                                  <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: "auto", opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="text-[10px] leading-relaxed text-slate-300 bg-cyber-bg/50 p-4 border border-white/5 rounded-xl"
                                  >
                                    <h5 className="font-display font-bold text-white text-[9px] uppercase tracking-wider mb-2 text-cyber-purple">
                                      AI EXECUTIVE SUMMARY
                                    </h5>
                                    {doc.ai_summary}
                                    <div className="mt-3 pt-3 border-t border-white/5">
                                      <h6 className="font-mono font-bold text-[9px] text-cyber-blue uppercase mb-1">
                                        Semantic Selection Explanation:
                                      </h6>
                                      <p className="italic text-slate-400 font-mono">"{doc.why_selected}"</p>
                                    </div>
                                  </motion.div>
                                </td>
                              </tr>
                            )}
                          </AnimatePresence>
                        </React.Fragment>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* REAL-TIME HR EMAIL LEDGER PERSISTED PANEL */}
            <div className="mt-6 pt-6 border-t border-cyber-purple/10">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-2 text-white">
                  <Clock className="w-4 h-4 text-cyber-blue" />
                  <h4 className="font-display font-bold text-xs uppercase tracking-wider">
                    RECENT HR MAIL DELIVERY LEDGER
                  </h4>
                </div>
                <button
                  onClick={fetchEmailLogs}
                  className="p-1 hover:bg-white/5 rounded-lg border border-white/5 hover:border-white/10 text-cyber-gray hover:text-white transition-all"
                  title="Sync Delivery Logs"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>

              {emailLogs.length === 0 ? (
                <div className="text-center py-6 border border-dashed border-white/5 rounded-xl text-[9px] text-cyber-gray/40">
                  No active HR email delivery logsPersisted inside MongoDB.
                </div>
              ) : (
                <div className="max-h-40 overflow-y-auto space-y-2 pr-2">
                  {emailLogs.map((log) => (
                    <div
                      key={log.delivery_id}
                      className="p-3 bg-cyber-bg/50 border border-white/5 rounded-lg flex items-center justify-between text-[10px] gap-4"
                    >
                      <div className="flex flex-col gap-1 min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white truncate max-w-[200px]" title={log.subject}>
                            {log.subject}
                          </span>
                          <span className="text-slate-400 font-mono text-[9px]">
                            to: {log.recipient}
                          </span>
                        </div>
                        <div className="text-[9px] text-cyber-gray truncate">
                          Attachments: {log.filenames.join(", ")}
                        </div>
                      </div>

                      <div className="flex items-center gap-4 flex-shrink-0">
                        <span className="text-[9px] font-mono text-cyber-gray/70">
                          {new Date(log.sent_at).toLocaleTimeString()}
                        </span>
                        
                        <span className={`px-2 py-0.5 rounded font-mono font-bold text-[8px] border uppercase ${
                          log.status === "Delivered" || log.status === "Mock-Delivered"
                            ? "bg-green-500/10 border-green-500/30 text-green-400"
                            : log.status === "Failed"
                            ? "bg-red-500/10 border-red-500/30 text-red-400"
                            : "bg-yellow-500/10 border-yellow-500/30 text-yellow-400 animate-pulse"
                        }`}>
                          {log.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </motion.div>
        )}

        {/* Search Results Display Grid */}
        <AnimatePresence>
          {searchResults.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 30 }}
              className="w-full max-w-7xl text-left mt-12"
            >
              <h2 className="font-display font-bold text-white tracking-widest text-sm mb-6 flex items-center gap-2 border-b border-cyber-blue/20 pb-3">
                <Terminal className="w-4.5 h-4.5 text-cyber-blue" />
                SCRAPED PUBLIC PORTAL SEARCH RESULT SHARDS
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {searchResults.map((card, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="cyber-glass p-5 rounded-xl border border-cyber-blue/15 hover:border-cyber-blue/30 transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-[9px] px-2 py-0.5 rounded bg-cyber-blue/10 border border-cyber-blue/20 text-cyber-blue uppercase font-bold tracking-wide">
                          {card.portal}
                        </span>
                        <span className="text-[10px] text-cyber-gray">
                          Similarity: <strong className="text-white">{card.relevance_score}%</strong>
                        </span>
                      </div>
                      
                      <h4 className="text-xs font-bold text-white mb-2 line-clamp-1">{card.title}</h4>
                      <p className="text-[11px] text-cyber-gray mb-4 leading-relaxed line-clamp-3">{card.snippet}</p>
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-white/5">
                      <span className="text-[10px] text-cyber-gray/70">Published: {card.published_date}</span>
                      
                      {card.url ? (
                        <a
                          href={card.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[10px] text-cyber-blue hover:underline flex items-center gap-1 font-semibold"
                        >
                          View Original Shard <ArrowRight className="w-3 h-3" />
                        </a>
                      ) : (
                        <span className="text-[10px] text-red-400">Offline</span>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* DOCUMENT PREVIEW DRAWER POPUP PANEL */}
      <AnimatePresence>
        {previewDoc && (
          <div className="fixed inset-0 z-50 flex justify-end">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setPreviewDoc(null)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="relative w-full max-w-xl bg-cyber-dark/95 border-l border-cyber-blue/20 p-6 flex flex-col h-full overflow-y-auto z-10 shadow-neon-blue select-text"
            >
              <button
                onClick={() => setPreviewDoc(null)}
                className="absolute top-4 right-4 p-1.5 hover:bg-white/5 rounded-lg border border-white/5 text-cyber-gray hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>

              <div className="mt-4">
                <span className="text-[9px] px-2 py-0.5 rounded bg-cyber-blue/10 border border-cyber-blue/20 text-cyber-blue font-bold font-mono tracking-wide uppercase">
                  {previewDoc.portal} Source Shard
                </span>
                <h3 className="text-sm font-bold text-white mt-2 leading-relaxed">
                  {previewDoc.filename}
                </h3>
                <span className="text-[10px] text-cyber-gray mt-1 block">
                  Published: {previewDoc.published_date} | Final Prioritized Score: <strong className="text-cyber-blue">{previewDoc.relevance_score}%</strong>
                </span>
              </div>

              {/* WHY SELECTED AI CALLOUT */}
              <div className="bg-cyber-purple/5 border border-cyber-purple/20 p-4 rounded-xl mt-6">
                <h4 className="font-display font-bold text-cyber-purple text-[9px] uppercase tracking-wider mb-1">
                  Why This Document Was Selected
                </h4>
                <p className="text-[10px] italic leading-relaxed text-slate-300 font-mono">
                  "{previewDoc.why_selected}"
                </p>
              </div>

              {/* 5-FACTOR SCORE BREAKDOWN VISUAL GAUGES */}
              <div className="mt-6 border-t border-white/5 pt-5">
                <h4 className="font-display font-bold text-white text-[9px] uppercase tracking-wider mb-4 flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-cyber-blue" />
                  AI 5-FACTOR MATHEMATICAL PRIORITY BREAKDOWN
                </h4>

                <div className="space-y-3">
                  {[
                    { label: "Semantic Similarity (40%)", score: previewDoc.semantic_similarity, color: "bg-cyber-blue" },
                    { label: "Keyword Match Density (25%)", score: previewDoc.keyword_match, color: "bg-cyber-purple" },
                    { label: "Recency Publication Factor (20%)", score: previewDoc.recency, color: "bg-cyber-indigo" },
                    { label: "Domain Trust Quality (10%)", score: previewDoc.source_quality, color: "bg-slate-400" },
                    { label: "Structural Completeness (5%)", score: previewDoc.document_completeness, color: "bg-green-400" }
                  ].map((gauge, gIdx) => (
                    <div key={gIdx} className="text-[10px]">
                      <div className="flex justify-between text-cyber-gray mb-1">
                        <span>{gauge.label}</span>
                        <span className="text-white font-mono font-bold">{gauge.score}%</span>
                      </div>
                      <div className="w-full bg-white/5 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full ${gauge.color}`}
                          style={{ width: `${gauge.score}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* EXPANDED SUMMARY */}
              <div className="mt-6 border-t border-white/5 pt-5">
                <h4 className="font-display font-bold text-white text-[9px] uppercase tracking-wider mb-2">
                  Ingested Executive Summary
                </h4>
                <p className="text-[10px] leading-relaxed text-slate-300 font-mono bg-cyber-bg/50 p-4 rounded-xl border border-white/5 whitespace-pre-wrap">
                  {previewDoc.ai_summary}
                </p>
              </div>

              {/* INLINE SOURCE EMBED PREVIEW */}
              <div className="mt-6 border-t border-white/5 pt-5 flex-1 flex flex-col min-h-0">
                <h4 className="font-display font-bold text-white text-[9px] uppercase tracking-wider mb-2 flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5 text-cyber-blue" />
                  Source Document Preview Shard
                </h4>
                
                <div className="bg-cyber-bg border border-white/5 rounded-xl p-4 flex-1 overflow-y-auto text-[10px] font-mono text-slate-400 min-h-[150px]">
                  {previewDoc.ai_summary.slice(0, 300)}... 
                  <br/><br/>
                  <span className="text-cyber-blue italic">
                    Note: Native inline rendering available. Inspect original document by clicking "Open Original" in triage actions.
                  </span>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* SEND TO HR EMAIL WIZARD MODAL DIALOG */}
      <AnimatePresence>
        {emailModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setEmailModalOpen(false)}
              className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            />
            
            <motion.div
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="relative w-full max-w-2xl bg-cyber-dark border border-cyber-purple/20 p-6 rounded-2xl shadow-neon-purple text-left flex flex-col max-h-[90vh] overflow-y-auto"
            >
              <button
                onClick={() => setEmailModalOpen(false)}
                className="absolute top-4 right-4 p-1.5 hover:bg-white/5 rounded-lg border border-white/5 text-cyber-gray hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>

              <div className="flex items-center gap-2 mb-4 border-b border-cyber-purple/20 pb-3">
                <Mail className="w-5 h-5 text-cyber-purple" />
                <h3 className="font-display font-black text-sm text-white tracking-wider uppercase">
                  HR DOCUMENT DELIVERY WIZARD
                </h3>
              </div>

              {emailDraftLoading ? (
                <div className="py-12 flex flex-col items-center justify-center">
                  <RefreshCw className="w-10 h-10 text-cyber-blue animate-spin mb-4" />
                  <h4 className="font-display font-bold text-xs text-white uppercase tracking-widest">
                    Generating Intelligent HR Email Draft...
                  </h4>
                </div>
              ) : (
                <div className="space-y-4 text-slate-200">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[9px] text-cyber-gray uppercase font-mono mb-1 font-bold">
                        Recipient HR Email:
                      </label>
                      <input
                        type="email"
                        value={recipientEmail}
                        onChange={(e) => setRecipientEmail(e.target.value)}
                        className="w-full bg-cyber-bg px-3 py-2 rounded-lg border border-white/10 text-[10px] text-white focus:outline-none focus:border-cyber-purple transition-all"
                      />
                    </div>
                    <div>
                      <label className="block text-[9px] text-cyber-gray uppercase font-mono mb-1 font-bold">
                        Email Subject:
                      </label>
                      <input
                        type="text"
                        value={emailSubject}
                        onChange={(e) => setEmailSubject(e.target.value)}
                        className="w-full bg-cyber-bg px-3 py-2 rounded-lg border border-white/10 text-[10px] text-white focus:outline-none focus:border-cyber-purple transition-all font-bold"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[9px] text-cyber-gray uppercase font-mono mb-1 font-bold">
                      Add Custom Message / Operator Note (Optional):
                    </label>
                    <textarea
                      value={customMessage}
                      onChange={(e) => setCustomMessage(e.target.value)}
                      placeholder="Add custom notes, urgency markers, or recipient directives here..."
                      rows={2}
                      className="w-full bg-cyber-bg px-3 py-2 rounded-lg border border-white/10 text-[10px] text-white focus:outline-none focus:border-cyber-purple transition-all font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[9px] text-cyber-gray uppercase font-mono mb-1 font-bold">
                      AI Generated Email Body:
                    </label>
                    <textarea
                      value={emailBody}
                      onChange={(e) => setEmailBody(e.target.value)}
                      rows={8}
                      className="w-full bg-cyber-bg px-4 py-3 rounded-lg border border-white/10 text-[10px] text-slate-300 focus:outline-none focus:border-cyber-purple transition-all font-mono whitespace-pre-wrap leading-relaxed"
                    />
                  </div>

                  <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3 text-[10px] flex items-center justify-between">
                    <div>
                      <span className="font-mono text-cyber-gray block">Attachments:</span>
                      <span className="font-bold text-white">
                        {selectedDocIds.length} prioritized documents
                      </span>
                    </div>
                    
                    <span className="text-[9px] px-2 py-0.5 rounded bg-cyber-blue/10 border border-cyber-blue/20 text-cyber-blue font-bold font-mono">
                      Background downloader active
                    </span>
                  </div>

                  <div className="flex justify-end gap-3 border-t border-cyber-purple/20 pt-4 mt-6">
                    <button
                      onClick={() => setEmailModalOpen(false)}
                      className="px-4 py-2 border border-white/5 hover:bg-white/5 text-[10px] text-cyber-gray hover:text-white rounded-lg transition-all"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleConfirmSendEmail}
                      disabled={sendingEmail}
                      className="bg-cyber-purple hover:bg-cyber-purple/80 text-white font-bold px-5 py-2.5 rounded-lg text-[10px] shadow-neon-purple flex items-center gap-1.5 transition-all"
                    >
                      {sendingEmail ? "SENDING..." : "CONFIRM & DISPATCH"}
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Footer Info Details */}
      <footer className="w-full max-w-7xl mx-auto px-6 pt-12 flex flex-col md:flex-row items-center justify-between text-xs text-cyber-gray/60 border-t border-t-white/5 relative z-20">
        <div className="flex items-center gap-2 mb-4 md:mb-0">
          <ShieldCheck className="w-4 h-4 text-cyber-blue" />
          <span>Grounded Document Guard Enabled | Temperature 0</span>
        </div>
        <div>
          <span>ALGONOX RAG MODEL © 2026</span>
        </div>
      </footer>
    </main>
  )
}
