---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary']
inputDocuments:
  - '_bmad-output/brainstorming/brainstorming-session-2026-03-16-001.md'
  - '_bmad-output/project-context.md'
  - 'docs/issues-cli-testing-001.md'
  - 'docs/issues-cli-testing-002.md'
  - 'docs/issues-cli-testing-003.md'
documentCounts:
  briefCount: 0
  researchCount: 0
  brainstormingCount: 1
  projectDocsCount: 4
classification:
  projectType: 'conversational_agent_platform'
  domain: 'event_coordination'
  complexity: 'high_operational_medium_regulatory'
  projectContext: 'brownfield'
  uxModel: 'conversational_first'
  mvpChannel: 'telegram_1to1'
  groupModel: 'informative_only'
  operationModel: 'autonomous_with_admin_escalation'
  architecture: 'modular_gateway_agnostic'
  skipSections: ['visual_design', 'responsive_design', 'wireframes']
  addSections: ['conversation_flows', 'permission_ux', 'error_messaging', 'channel_feature_matrix', 'escalation_protocol']
workflowType: 'prd'
---

# Product Requirements Document - Kalendbot

**Author:** Kmiloaparicio
**Date:** 2026-03-20

## Executive Summary

Kalendbot es un agente conversacional autónomo que coordina los 30 eventos anuales de la Asociación Holandesa en México (NV Mexico) con 9 proveedores mediante Telegram (MVP) y WhatsApp (fase posterior). El sistema reemplaza la coordinación manual que hoy recae completamente en el presidente de la asociación (Rocco van Velzen), quien gestiona fechas, conflictos, estados de eventos, flyers y seguimiento de proveedores a través de un grupo de WhatsApp.

Kalendbot absorbe el trabajo operativo — detección de conflictos, validación de reglas de negocio, seguimiento de estados, recordatorios — y otorga autonomía a los proveedores para gestionar sus propios eventos dentro de las reglas establecidas. Rocco pasa de coordinador activo a supervisor estratégico, interviniendo únicamente como árbitro final cuando los contactos no logran resolver conflictos entre sí.

El modelo de operación es chat privado 1-a-1 entre cada contacto y el bot, con un grupo informativo donde el bot publica notificaciones sin recibir ni procesar mensajes.

### What Makes This Special

Kalendbot no es un calendario compartido ni un chatbot genérico. Es un **agente de coordinación con inteligencia de negocio integrada**: entiende y aplica automáticamente las reglas de NV Mexico — tiers de proveedores, precedencia entre eventos, restricciones de fechas, feriados mexicanos y holandeses — vía conversación natural en español.

El insight central es que la IA conversacional ya permite que un bot entienda lenguaje natural Y coordine con reglas complejas de negocio, eliminando la necesidad de un intermediario humano para cada interacción. Los proveedores se auto-gestionan; el sistema valida automáticamente cada modificación contra ConflictDetector y RulesEngine antes de aplicarla.

## Project Classification

| Campo | Valor |
|-------|-------|
| **Tipo de proyecto** | Conversational Agent Platform (multi-gateway chatbot) |
| **Dominio** | Event Coordination (resource scheduling para asociaciones) |
| **Complejidad** | Alta (operacional) / Media (regulatoria) |
| **Contexto** | Brownfield — MVP existente con 8 tools, agente LangChain/LangGraph, CLI operativo |
| **Modelo UX** | Conversational-first (sin UI visual propia) |
| **Canal MVP** | Telegram 1-a-1 (WhatsApp en fase posterior) |
| **Modelo de grupo** | Informativo only (bot publica, no recibe) |
| **Modelo operativo** | Autónomo con escalación a admin (Rocco árbitro final) |
| **Arquitectura** | Modular, gateway-agnostic. Event coordination como módulo 1 |
| **Sistema de permisos** | 5 roles: admin, content_manager, proveedor, readonly, blocked |
