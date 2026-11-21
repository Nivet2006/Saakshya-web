'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface AmbientBackgroundProps {
  intensity?: number;
}

/**
 * AmbientBackground — Organic glowing slow-moving blobs creating a
 * calm, living healthcare atmosphere behind landing and dashboard areas.
 */
export const AmbientBackground: React.FC<AmbientBackgroundProps> = ({ intensity = 1 }) => {
  return (
    <div
      aria-hidden="true"
      className="fixed inset-0 overflow-hidden pointer-events-none z-0"
    >
      {/* Blob A — top-left, large soft clinical teal */}
      <motion.div
        animate={{
          x: [0, 28, -10, 0],
          y: [0, -18, 14, 0],
          scale: [1, 1.1, 0.96, 1],
        }}
        transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', repeatType: 'mirror' }}
        style={{
          position: 'absolute',
          top: '-12%',
          left: '-10%',
          width: '52vw',
          height: '52vw',
          maxWidth: 640,
          maxHeight: 640,
          borderRadius: '60% 40% 70% 30% / 55% 65% 35% 45%',
          background: 'radial-gradient(ellipse at center, rgba(13, 148, 136, 0.14) 0%, transparent 70%)',
          filter: 'blur(52px)',
          opacity: intensity,
        }}
      />

      {/* Blob B — bottom-right, medium soft emerald */}
      <motion.div
        animate={{
          x: [0, -24, 12, 0],
          y: [0, 16, -20, 0],
          scale: [1, 1.07, 1.12, 1],
        }}
        transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut', delay: 1.5, repeatType: 'mirror' }}
        style={{
          position: 'absolute',
          bottom: '-15%',
          right: '-12%',
          width: '60vw',
          height: '60vw',
          maxWidth: 700,
          maxHeight: 700,
          borderRadius: '40% 60% 30% 70% / 65% 35% 65% 35%',
          background: 'radial-gradient(ellipse at center, rgba(16, 185, 129, 0.12) 0%, transparent 70%)',
          filter: 'blur(60px)',
          opacity: intensity,
        }}
      />

      {/* Blob C — center-right, breathing ambient glow */}
      <motion.div
        animate={{
          opacity: [0.05, 0.14, 0.05],
          scale: [1, 1.15, 1],
        }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut', delay: 0.8, repeatType: 'mirror' }}
        style={{
          position: 'absolute',
          top: '30%',
          left: '35%',
          width: '45vw',
          height: '45vw',
          maxWidth: 500,
          maxHeight: 500,
          borderRadius: '50%',
          background: 'radial-gradient(ellipse at center, rgba(14, 116, 144, 0.25) 0%, transparent 65%)',
          filter: 'blur(84px)',
        }}
      />
    </div>
  );
};
