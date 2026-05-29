"use client"

import React from "react"
import { motion } from "framer-motion"

export default function InfinityLogo({ size = 180 }: { size?: number }) {
  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      
      {/* Background Subtle Tech Orbit Rings */}
      <motion.svg
        width={size * 1.3}
        height={size * 1.3}
        viewBox="0 0 200 200"
        className="absolute opacity-20"
        animate={{ rotate: 360 }}
        transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
      >
        <circle cx="100" cy="100" r="85" fill="none" stroke="#00f0ff" strokeWidth="0.5" strokeDasharray="3 6" />
        <circle cx="100" cy="100" r="70" fill="none" stroke="#d946ef" strokeWidth="1" strokeDasharray="20 40 10 30" />
        {/* Radial Tech Circuit Node Indicators */}
        <line x1="100" y1="15" x2="100" y2="30" stroke="#00f0ff" strokeWidth="2" />
        <line x1="100" y1="170" x2="100" y2="185" stroke="#d946ef" strokeWidth="2" />
        <circle cx="100" cy="30" r="3" fill="#00f0ff" />
        <circle cx="100" cy="170" r="3" fill="#d946ef" />
      </motion.svg>

      <motion.svg
        width={size * 1.1}
        height={size * 1.1}
        viewBox="0 0 200 200"
        className="absolute opacity-30"
        animate={{ rotate: -360 }}
        transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
      >
        <circle cx="100" cy="100" r="60" fill="none" stroke="#8b5cf6" strokeWidth="0.5" strokeDasharray="5 15" />
      </motion.svg>

      {/* Primary Metallic Infinity SVG */}
      <svg
        width={size}
        height={size * 0.6}
        viewBox="0 0 100 50"
        xmlns="http://www.w3.org/2000/svg"
        className="relative z-10 filter drop-shadow-[0_0_15px_rgba(139,92,246,0.5)]"
      >
        <defs>
          {/* Neon Blue-Purple Metallic Gradients */}
          <linearGradient id="metallic-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00f0ff" />
            <stop offset="35%" stopColor="#00c8ff" />
            <stop offset="65%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#d946ef" />
          </linearGradient>

          {/* Electric pulse gradient */}
          <linearGradient id="pulse-grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="transparent" stopOpacity="0" />
            <stop offset="50%" stopColor="#ffffff" stopOpacity="1" />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </linearGradient>

          {/* 3D Lighting Filter for Chrome/Metallic Bevel Effect */}
          <filter id="metallic-bevel" x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="1.5" result="blur" />
            <feSpecularLighting in="blur" surfaceScale="5" specularConstant="1.2" specularExponent="40" lightingColor="#ffffff" result="specular">
              <fePointLight x="-50" y="-100" z="200" />
            </feSpecularLighting>
            <feComposite in="specular" in2="SourceAlpha" operator="in" result="specularComposite" />
            <feComposite in="SourceGraphic" in2="specularComposite" operator="arithmetic" k1="0" k2="1" k3="1" k4="0" result="litGraphic" />
          </filter>
        </defs>

        {/* Outer Glow Path */}
        <path
          d="M 25 12.5 C 10 12.5 10 37.5 25 37.5 C 40 37.5 60 12.5 75 12.5 C 90 12.5 90 37.5 75 37.5 C 60 37.5 40 12.5 25 12.5 Z"
          fill="none"
          stroke="url(#metallic-grad)"
          strokeWidth="6"
          strokeLinecap="round"
          filter="url(#metallic-bevel)"
        />

        {/* Inner Circuit Track Detail */}
        <path
          d="M 25 12.5 C 10 12.5 10 37.5 25 37.5 C 40 37.5 60 12.5 75 12.5 C 90 12.5 90 37.5 75 37.5 C 60 37.5 40 12.5 25 12.5 Z"
          fill="none"
          stroke="#00f0ff"
          strokeWidth="0.8"
          strokeDasharray="12 6 3 6"
          className="opacity-90"
        />

        {/* Dynamic Electric Laser Dot Circuit Flow */}
        <path
          d="M 25 12.5 C 10 12.5 10 37.5 25 37.5 C 40 37.5 60 12.5 75 12.5 C 90 12.5 90 37.5 75 37.5 C 60 37.5 40 12.5 25 12.5 Z"
          fill="none"
          stroke="url(#pulse-grad)"
          strokeWidth="4"
          strokeDasharray="20 80"
          strokeDashoffset="0"
        >
          <animate
            attributeName="stroke-dashoffset"
            values="100;0"
            dur="3.5s"
            repeatCount="indefinite"
            keyTimes="0;1"
          />
        </path>
      </svg>
      
      {/* Central Pulsating Core Node */}
      <div className="absolute w-2.5 h-2.5 bg-white rounded-full filter blur-[1px] shadow-[0_0_12px_#00f0ff] animate-ping" />
      <div className="absolute w-1.5 h-1.5 bg-cyber-blue rounded-full filter shadow-[0_0_8px_#ffffff]" />
    </div>
  )
}
