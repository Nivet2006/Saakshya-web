'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface HealthWaveProps {
  width?: number;
  height?: number;
  color?: string;
  opacity?: number;
}

/**
 * HealthWave — Animated SVG healthcare vitals waveform.
 * Slowly animates across the path to reflect active clinical monitoring.
 */
export const HealthWave: React.FC<HealthWaveProps> = ({
  width = 320,
  height = 48,
  color = '#0D9488',
  opacity = 0.45,
}) => {
  const path = `M0,24 C20,24 30,8 50,8 C70,8 80,40 100,40 C120,40 130,4 150,4 C170,4 180,36 200,36 C220,36 230,16 250,16 C270,16 280,32 300,32 C320,32 330,12 350,12 L${width},24`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="block overflow-visible"
    >
      <motion.path
        d={path}
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={opacity}
        strokeDasharray="1000"
        initial={{ strokeDashoffset: 1000, opacity: 0 }}
        animate={{ strokeDashoffset: 0, opacity }}
        transition={{ duration: 1.8, ease: 'easeOut', delay: 0.3 }}
      />
      {/* Continuous waveform flow */}
      <motion.path
        d={path}
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        opacity={opacity * 0.6}
        strokeDasharray="60 20"
        animate={{ strokeDashoffset: [0, -80] }}
        transition={{ duration: 3.5, repeat: Infinity, ease: 'linear' }}
      />
    </svg>
  );
};
