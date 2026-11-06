---
name: SmartDesk Precision System
colors:
  surface: '#0f131c'
  surface-dim: '#0f131c'
  surface-bright: '#353942'
  surface-container-lowest: '#0a0e16'
  surface-container-low: '#181c24'
  surface-container: '#1c2028'
  surface-container-high: '#262a33'
  surface-container-highest: '#31353e'
  on-surface: '#dfe2ee'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#dfe2ee'
  inverse-on-surface: '#2c3039'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#d0bcff'
  on-secondary: '#3c0091'
  secondary-container: '#571bc1'
  on-secondary-container: '#c4abff'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#00a572'
  on-tertiary-container: '#00311f'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#0f131c'
  on-background: '#dfe2ee'
  surface-variant: '#31353e'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  metric-num:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-dense: 0.5rem
  margin: 1.5rem
  margin-compact: 1rem
  space-2xs: 0.125rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
  space-2xl: 2rem
---

## Brand & Style

This design system establishes a high-performance, developer-grade workspace tailored for IT service management, incident orchestration, and enterprise asset workflows. Combining the kinetic velocity of Linear with the operational depth of enterprise ServiceNow architectures, the aesthetic balances high information density with refined clarity.

### Personality & Core Attributes
- **Precise & Systematic:** Crisp geometry, structured alignment grids, exact 1px data boundaries, and strict functional hierarchy.
- **Instrumental & Quiet:** Surfaces serve data without visual competition; vibrant status and severity accents guide the operator’s eye.
- **Authoritative & Trustworthy:** Enterprise-grade durability rendered through deep navy charcoals and crisp slate boundaries.
- **Intelligent:** Subtle violet illumination denoting automated triage, predictive resolution, and agentic actions without clutter.

### Visual Style
A hybrid of **Minimalist Precision** and **Modern Dark-Mode Craftsmanship**:
- Deliberate use of subtle 1px border strokes rather than deep dropshadows.
- Dense, scan-friendly data structures with immediate keyboard and mouse affinity.
- High-contrast visual tagging for SLA tracking, priority matrices, and state changes.

## Colors

The system operates across both dark and light environments, with the dark palette configured as the default standard for focused technical work.

### Color Tiers & Surface Scales

#### Dark Mode (Primary Mode)
- **Base Canvas:** `#0B0F17` (Deep Obsidian Navy)
- **Surface Level 1 (Sidebar/App Bar):** `#111827` (Slate Midnight)
- **Surface Level 2 (Cards, Drawers, Panels):** `#151E2E` (Deep Navy Charcoal)
- **Surface Level 3 (Hover states, Active Cells, Popovers):** `#1E293B` (Elevated Slate)
- **Border / Hairline Dividers:** `#1F2937` (Subtle boundary), `#374151` (High-contrast boundary & active outlines)
- **Foreground Neutral (Text Primary):** `#F9FAFB`
- **Foreground Muted (Text Secondary):** `#94A3B8`
- **Foreground Tertiary (Text De-emphasized):** `#64748B`

#### Light Mode
- **Base Canvas:** `#F8FAFC` (Cool Off-White)
- **Surface Level 1 (Panels & Headers):** `#FFFFFF` (Pure White)
- **Surface Level 2 (Nested Groupings, Tables):** `#F1F5F9` (Subtle Ash)
- **Border / Hairline Dividers:** `#E2E8F0` (Default), `#CBD5E1` (Input & card active)
- **Foreground Neutral (Text Primary):** `#0F172A`
- **Foreground Muted (Text Secondary):** `#475569`
- **Foreground Tertiary (Text De-emphasized):** `#94A3B8`

### Accent & Semantic Tokens
- **Brand & Action (Electric Blue):** `#3B82F6` (Hover: `#2563EB`, Subtle Fill: `rgba(59, 130, 246, 0.12)`)
- **Intelligence & Automation (AI Violet):** `#8B5CF6` (Secondary: `#6366F1`, Subtle Fill: `rgba(139, 92, 246, 0.12)`)
- **Status: Success / Resolved (Emerald):** `#10B981` (Subtle Fill: `rgba(16, 185, 129, 0.12)`)
- **Status: Warning / Investigating (Amber):** `#F59E0B` (Subtle Fill: `rgba(245, 158, 11, 0.12)`)
- **Status: Error / Critical Incident (Crimson):** `#EF4444` (Subtle Fill: `rgba(239, 68, 68, 0.12)`)

## Typography

Typography relies on **Inter** with tabular figure features enabled (`tnum`, `cv05`, `cv11`) to ensure optimal scan rates across ticket queues, time logs, and metric cards.

### Scaling & Roles
- **Metrics & KPIs (`metric-num`):** Used strictly for high-level incident totals, SLA counters, and MTTR summaries.
- **Interface Body (`body-md` / `13px`):** Optimized for high-density tables and complex forms, reducing scrolling while maintaining legibility.
- **Badges & Meta (`label-sm` / `11px`):** Used for issue states, severity indicators, and breadcrumb tags.
- **Display Weights:** Reserved strictly for root dashboard milestones and incident triage overviews to preserve layout structure.

## Layout & Spacing

The layout model is governed by an engineering-first **fluid workspace layout** split into collapsible primary navigation (64px mini / 240px full), contextual side panels (320px–420px), and an infinite fluid center workspace.

### Grid & Density Principles
- **Desktop (>= 1280px):** 12-column variable fluid grid with `1rem` gutters for standard views. For tabular queues and incident command centers, `gutter-dense` (`0.5rem`) is applied to maximize horizontal data density.
- **Tablet (768px – 1279px):** Content compresses into a 6-column fluid canvas; right-hand inspect drawers transform into slide-over sheets.
- **Mobile (< 768px):** Single-column stack with `margin-compact` (`1rem`) outer padding. Side navigation collapses to an off-canvas drawer.

### Spacing Rhythm
- **Internal Component Padding:** Controlled by `space-xs` (4px) to `space-md` (12px) to prevent vertical bloating in forms and tables.
- **Layout Separation:** Structural panels and content groupings leverage `space-lg` (16px) and `space-xl` (24px) gaps to maintain distinct focus zones.

## Elevation & Depth

This system intentionally departs from diffuse, heavy drop shadows, relying instead on **low-contrast outlines, dark surface layering, and luminous edge highlights**.

### Surface Tiering
1. **Base Tier (Ground):** The darkest/lightest plane (`#0B0F17` / `#F8FAFC`). Pure canvas containing background queues and static toolbars.
2. **Structural Tier (Plates & Cards):** Raised one tone higher (`#151E2E` / `#FFFFFF`), framed with a crisp `1px solid #1F2937` (dark) or `1px solid #E2E8F0` (light).
3. **Floating Tier (Menus, Command Palettes, Popovers):** Highest surface tone (`#1E293B` / `#FFFFFF`). Casts an ultra-crisp directional shadow: `0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.08)`.

### Subtle Luminescence
- **AI Automation Borders:** Contextual actions and automated suggestions incorporate a soft radial violet edge glow: `box-shadow: 0 0 0 1px #8B5CF6, 0 0 12px -2px rgba(139, 92, 246, 0.25)`.
- **Keyboard Focus States:** Electric blue ring with zero blur: `box-shadow: 0 0 0 2px #0B0F17, 0 0 0 4px #3B82F6`.

## Shapes

The design system implements a **Soft (Level 1)** geometric standard. This provides an enterprise-grade technical feel: sharp enough to communicate engineering discipline, with just enough curvature to maintain visual comfort.

### Corner Radius Mapping
- **Input Fields, Badges, Buttons:** `0.25rem` (4px) base border radius.
- **Cards, Modals, Flyout Panels:** `0.5rem` (8px) (`rounded-lg`).
- **Command Palettes & Hero Overlays:** `0.75rem` (12px) (`rounded-xl`).
- **Status Dots & Avatars:** Fully rounded circular geometry (`rounded-full`).

## Components

### Buttons
- **Primary:** Solid `#3B82F6`, foreground `#FFFFFF`, `0.25rem` radius, subtle top-edge highlight inset (`inset 0 1px 0 rgba(255,255,255,0.15)`). Hover: `#2563EB`.
- **Secondary:** Surface `#151E2E`, border `1px solid #374151`, text `#F9FAFB`. Hover: surface `#1E293B`.
- **Subtle / Ghost:** Transparent background, text `#94A3B8`. Hover: `#1E293B` background, text `#F9FAFB`.
- **AI Action Button:** Background `rgba(139, 92, 246, 0.12)`, border `1px solid rgba(139, 92, 246, 0.4)`, text `#C4B5FD`. Hover: background `rgba(139, 92, 246, 0.2)`.

### Status & Priority Badges (Chips)
- **Geometry:** Height 20px, horizontal padding `6px`, font size `11px`, font weight `500`, radius `4px`.
- **Status (Open):** Blue tint (`bg: rgba(59, 130, 246, 0.1)`, `border: rgba(59, 130, 246, 0.2)`, `text: #60A5FA`).
- **Status (In Progress):** Amber tint (`bg: rgba(245, 158, 11, 0.1)`, `border: rgba(245, 158, 11, 0.2)`, `text: #FBBF24`).
- **Status (Resolved):** Emerald tint (`bg: rgba(16, 185, 129, 0.1)`, `border: rgba(16, 185, 129, 0.2)`, `text: #34D399`).
- **Priority (Critical):** Crimson tint with pulse indicator dot (`bg: rgba(239, 68, 68, 0.15)`, `border: rgba(239, 68, 68, 0.3)`, `text: #F87171`).

### Data Tables & Queue Lists
- **Structure:** Compact `36px` to `40px` row heights for standard ticket views; `28px` condensed mode.
- **Divider:** Continuous `1px solid #1F2937` row separators.
- **States:** Hover reveals background `#151E2E` with active keyboard focus displaying a subtle 2px solid `#3B82F6` left-indicator rail.

### Input Fields & Controls
- **Inputs:** Dark mode background `#111827`, border `1px solid #374151`, text `#F9FAFB`, placeholder `#64748B`. Focused state: border `#3B82F6` with crisp outline.
- **Checkboxes & Radios:** `16px x 16px`, background `#111827`, border `1px solid #374151`. Checked state transitions immediately to `#3B82F6` fill with pure white glyphs.

### Cards & Ticket Detail Panels
- **Structure:** Background `#151E2E`, border `1px solid #1F2937`, internal padding `16px`.
- **Header:** Distinct hairline divider separating breadcrumb metadata from ticket description and timeline activities.
- **Quick-Actions Bar:** Embedded at the bottom or top-right with icon-only or micro-label controls (SLA timer, assignee selector, escalate button).