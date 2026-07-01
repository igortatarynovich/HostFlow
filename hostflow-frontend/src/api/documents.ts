/**
 * Documents API - Backward compatibility re-export
 * 
 * This file re-exports everything from the modular structure in ./documents/
 * to maintain backward compatibility with existing imports.
 * 
 * New code should import directly from ./documents/ modules for better tree-shaking.
 */

export * from "./documents/index";

