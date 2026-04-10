"use client";

import { ReactNode } from "react";
import { motion } from "framer-motion";
import {
  containerVariants,
  itemVariants,
  floatingVariants,
  slideUpVariants,
} from "@/lib/animations";

interface AnimatedContainerProps {
  children: ReactNode;
  className?: string;
  stagger?: boolean;
}

export function AnimatedContainer({
  children,
  className = "",
  stagger = true,
}: AnimatedContainerProps) {
  return (
    <motion.div
      className={className}
      variants={stagger ? containerVariants : undefined}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.2 }}
    >
      {children}
    </motion.div>
  );
}

interface AnimatedItemProps {
  children: ReactNode;
  className?: string;
  delay?: number;
}

export function AnimatedItem({
  children,
  className = "",
  delay = 0,
}: AnimatedItemProps) {
  return (
    <motion.div
      className={className}
      variants={itemVariants}
      transition={{ delay }}
    >
      {children}
    </motion.div>
  );
}

interface FloatingElementProps {
  children: ReactNode;
  className?: string;
}

export function FloatingElement({ children, className = "" }: FloatingElementProps) {
  return (
    <motion.div
      className={className}
      variants={floatingVariants}
      initial="initial"
      animate="animate"
    >
      {children}
    </motion.div>
  );
}

interface SlideUpProps {
  children: ReactNode;
  className?: string;
  delay?: number;
}

export function SlideUp({ children, className = "", delay = 0 }: SlideUpProps) {
  return (
    <motion.div
      className={className}
      variants={slideUpVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.2 }}
      transition={{ delay }}
    >
      {children}
    </motion.div>
  );
}
