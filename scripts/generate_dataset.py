#!/usr/bin/env python3
"""
AI Diagram Generator — Reproducible Multi-Family Dataset Generator.
Generates structured text-to-diagram dataset with Intermediate Representation (IR) graphs,
ensuring zero data leakage across template-isolated Train (approx 70%), Val (approx 15%), and Test (approx 15%) splits.
"""

import os
import json
import random
import argparse
from pathlib import Path
from typing import Dict, List, Any


def get_flowchart_templates() -> List[Dict[str, Any]]:
    return [
        {
            "template_id": "flow_user_auth_retry",
            "domain": "security",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"When a user signs in with {v['auth_method']}, the system validates credentials against {v['auth_store']}. If credentials match, the system issues an auth token and redirects to {v['landing_page']}. If authentication fails, the system increments the retry counter. If retries exceed {v['max_retries']}, the system locks the account; otherwise, it displays an error and prompts the user to re-enter credentials.",
                    "nodes": [
                        {"id": "n1", "label": f"User submits {v['auth_method']}", "type": "terminal"},
                        {"id": "n2", "label": f"Validate against {v['auth_store']}", "type": "process"},
                        {"id": "n3", "label": "Credentials valid?", "type": "decision"},
                        {"id": "n4", "label": f"Issue token & redirect to {v['landing_page']}", "type": "terminal"},
                        {"id": "n5", "label": "Increment retry counter", "type": "process"},
                        {"id": "n6", "label": f"Retries > {v['max_retries']}?", "type": "decision"},
                        {"id": "n7", "label": "Lock account & alert admin", "type": "terminal"},
                        {"id": "n8", "label": "Display error & prompt re-entry", "type": "process"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "submits", "edge_type": "flow", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "checks", "edge_type": "flow", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "Yes", "edge_type": "branch_yes", "directed": True},
                        {"id": "e4", "source": "n3", "target": "n5", "label": "No", "edge_type": "branch_no", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n6", "label": "evaluated", "edge_type": "flow", "directed": True},
                        {"id": "e6", "source": "n6", "target": "n7", "label": "Yes", "edge_type": "branch_yes", "directed": True},
                        {"id": "e7", "source": "n6", "target": "n8", "label": "No", "edge_type": "branch_no", "directed": True},
                        {"id": "e8", "source": "n8", "target": "n1", "label": "retry", "edge_type": "loop_back", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"auth_method": "username and password", "auth_store": "PostgreSQL database", "landing_page": "User Dashboard", "max_retries": "3"},
                {"auth_method": "corporate SSO email", "auth_store": "Active Directory LDAP", "landing_page": "Intranet Home", "max_retries": "5"}
            ]
        },
        {
            "template_id": "flow_assignment_review",
            "domain": "education",
            "complexity": "simple",
            "generators": [
                lambda v: {
                    "text": f"When a student submits {v['submission_type']}, the {v['reviewer']} evaluates the work. If it is approved, the {v['system']} publishes {v['outcome']}. Otherwise, the student corrects the errors and resubmits it for review.",
                    "nodes": [
                        {"id": "n1", "label": f"Student submits {v['submission_type']}", "type": "terminal"},
                        {"id": "n2", "label": f"{v['reviewer']} reviews submission", "type": "process"},
                        {"id": "n3", "label": "Approved?", "type": "decision"},
                        {"id": "n4", "label": f"{v['system']} publishes {v['outcome']}", "type": "terminal"},
                        {"id": "n5", "label": "Student corrects errors", "type": "process"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "submit", "edge_type": "flow", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "evaluate", "edge_type": "flow", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "Yes", "edge_type": "branch_yes", "directed": True},
                        {"id": "e4", "source": "n3", "target": "n5", "label": "No", "edge_type": "branch_no", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n2", "label": "resubmit", "edge_type": "loop_back", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"submission_type": "programming assignment", "reviewer": "teaching assistant", "system": "LMS portal", "outcome": "final grade and feedback"},
                {"submission_type": "capstone project report", "reviewer": "faculty committee", "system": "Academic Registry", "outcome": "project approval"}
            ]
        },
        {
            "template_id": "flow_order_fulfillment",
            "domain": "commerce",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"When an order is placed on the {v['channel']}, the inventory system checks stock availability for {v['item']}. If in stock, payment is charged via {v['payment_method']}, the warehouse packs the parcel, and a dispatch notification is sent. If out of stock, the customer is notified and offered a backorder option.",
                    "nodes": [
                        {"id": "n1", "label": f"Order received via {v['channel']}", "type": "terminal"},
                        {"id": "n2", "label": f"Check stock for {v['item']}", "type": "process"},
                        {"id": "n3", "label": "Item in stock?", "type": "decision"},
                        {"id": "n4", "label": f"Charge via {v['payment_method']}", "type": "process"},
                        {"id": "n5", "label": "Pack and ship parcel", "type": "process"},
                        {"id": "n6", "label": "Dispatch notification sent", "type": "terminal"},
                        {"id": "n7", "label": "Notify out-of-stock & offer backorder", "type": "terminal"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "receives", "edge_type": "flow", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "evaluates", "edge_type": "flow", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "Yes", "edge_type": "branch_yes", "directed": True},
                        {"id": "e4", "source": "n3", "target": "n7", "label": "No", "edge_type": "branch_no", "directed": True},
                        {"id": "e5", "source": "n4", "target": "n5", "label": "paid", "edge_type": "flow", "directed": True},
                        {"id": "e6", "source": "n5", "target": "n6", "label": "shipped", "edge_type": "flow", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"channel": "mobile app", "item": "electronics gadget", "payment_method": "credit card"},
                {"channel": "web storefront", "item": "textbook package", "payment_method": "PayPal checkout"}
            ]
        },
        {
            "template_id": "flow_incident_triage",
            "domain": "devops",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"An automated monitoring alert triggers for {v['service_name']}. The on-call engineer checks severity. If severity is Critical, trigger P1 incident response, page {v['responder_team']}, and initiate failover. If severity is Low, log the warning to {v['log_system']} and create a Jira backlog ticket.",
                    "nodes": [
                        {"id": "n1", "label": f"Monitoring alert on {v['service_name']}", "type": "terminal"},
                        {"id": "n2", "label": "Evaluate incident severity", "type": "decision"},
                        {"id": "n3", "label": f"Page {v['responder_team']} (P1)", "type": "process"},
                        {"id": "n4", "label": "Initiate automated failover", "type": "terminal"},
                        {"id": "n5", "label": f"Log warning to {v['log_system']}", "type": "process"},
                        {"id": "n6", "label": "Create backlog ticket", "type": "terminal"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "alert fires", "edge_type": "flow", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "Critical", "edge_type": "branch_yes", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "execute", "edge_type": "flow", "directed": True},
                        {"id": "e4", "source": "n2", "target": "n5", "label": "Low", "edge_type": "branch_no", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n6", "label": "file", "edge_type": "flow", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"service_name": "Payment Gateway API", "responder_team": "Core Platform SRE", "log_system": "Datadog logs"},
                {"service_name": "Auth Token Service", "responder_team": "Security Operations", "log_system": "Splunk indexer"}
            ]
        },
        {
            "template_id": "flow_atm_cash_withdrawal",
            "domain": "banking",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"ATM cash withdrawal workflow: The customer inserts their {v['card_type']} and enters their PIN. The ATM validates the PIN. If the PIN is incorrect, display an invalid PIN error. If correct, check account balance. If the balance exceeds the requested {v['amount_desc']}, dispense cash and print receipt; otherwise, display insufficient funds.",
                    "nodes": [
                        {"id": "n1", "label": f"Insert {v['card_type']} & enter PIN", "type": "terminal"},
                        {"id": "n2", "label": "Verify PIN", "type": "decision"},
                        {"id": "n3", "label": "Display invalid PIN error", "type": "terminal"},
                        {"id": "n4", "label": "Check account balance", "type": "process"},
                        {"id": "n5", "label": f"Balance >= {v['amount_desc']}?", "type": "decision"},
                        {"id": "n6", "label": "Dispense cash & print receipt", "type": "terminal"},
                        {"id": "n7", "label": "Display insufficient funds error", "type": "terminal"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "validate", "edge_type": "flow", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "Incorrect", "edge_type": "branch_no", "directed": True},
                        {"id": "e3", "source": "n2", "target": "n4", "label": "Correct", "edge_type": "branch_yes", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "check balance", "edge_type": "flow", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n6", "label": "Yes", "edge_type": "branch_yes", "directed": True},
                        {"id": "e6", "source": "n5", "target": "n7", "label": "No", "edge_type": "branch_no", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"card_type": "debit card", "amount_desc": "requested amount"},
                {"card_type": "smart chip card", "amount_desc": "withdrawal sum"}
            ]
        },
        {
            "template_id": "flow_bug_triage_lifecycle",
            "domain": "software_engineering",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Bug triage workflow in {v['tracker_name']}: A new defect is reported by {v['reporter']}. The QA lead inspects for reproducibility. If not reproducible, request more info from reporter. If reproducible, check if it is a duplicate. If duplicate, link to parent ticket and close; otherwise, assign priority and assign to {v['dev_team']} for resolution.",
                    "nodes": [
                        {"id": "n1", "label": f"Bug filed in {v['tracker_name']}", "type": "terminal"},
                        {"id": "n2", "label": "Is defect reproducible?", "type": "decision"},
                        {"id": "n3", "label": "Request info & close if inactive", "type": "terminal"},
                        {"id": "n4", "label": "Is defect duplicate?", "type": "decision"},
                        {"id": "n5", "label": "Link duplicate and close", "type": "terminal"},
                        {"id": "n6", "label": f"Assign to {v['dev_team']} for fix", "type": "terminal"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "triage", "edge_type": "flow", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "No", "edge_type": "branch_no", "directed": True},
                        {"id": "e3", "source": "n2", "target": "n4", "label": "Yes", "edge_type": "branch_yes", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "Yes", "edge_type": "branch_yes", "directed": True},
                        {"id": "e5", "source": "n4", "target": "n6", "label": "No", "edge_type": "branch_no", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"tracker_name": "Jira Service Desk", "reporter": "beta tester", "dev_team": "core backend team"},
                {"tracker_name": "GitHub Issues", "reporter": "community user", "dev_team": "frontend maintainers"}
            ]
        }
    ]


def get_architecture_templates() -> List[Dict[str, Any]]:
    return [
        {
            "template_id": "arch_ecommerce_microservices",
            "domain": "cloud_systems",
            "complexity": "complex",
            "generators": [
                lambda v: {
                    "text": f"Architecture for an e-commerce platform: {v['client']} sends HTTP requests through {v['gateway']}. The gateway routes catalog queries to {v['catalog_service']} and order transactions to {v['order_service']}. {v['catalog_service']} reads from {v['cache']} and falls back to {v['database']}. {v['order_service']} writes transactions to {v['database']} and emits events to {v['message_broker']}. {v['payment_service']} processes transactions via {v['payment_gateway']}.",
                    "nodes": [
                        {"id": "n1", "label": v["client"], "type": "client"},
                        {"id": "n2", "label": v["gateway"], "type": "api_gateway"},
                        {"id": "n3", "label": v["catalog_service"], "type": "service"},
                        {"id": "n4", "label": v["order_service"], "type": "service"},
                        {"id": "n5", "label": v["cache"], "type": "cache"},
                        {"id": "n6", "label": v["database"], "type": "database"},
                        {"id": "n7", "label": v["message_broker"], "type": "message_broker"},
                        {"id": "n8", "label": v["payment_service"], "type": "service"},
                        {"id": "n9", "label": v["payment_gateway"], "type": "external_system"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "HTTPS requests", "edge_type": "http_request", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "/products route", "edge_type": "http_request", "directed": True},
                        {"id": "e3", "source": "n2", "target": "n4", "label": "/orders route", "edge_type": "http_request", "directed": True},
                        {"id": "e4", "source": "n3", "target": "n5", "label": "query cache", "edge_type": "cache_lookup", "directed": True},
                        {"id": "e5", "source": "n3", "target": "n6", "label": "read catalog", "edge_type": "db_read_write", "directed": True},
                        {"id": "e6", "source": "n4", "target": "n6", "label": "write order", "edge_type": "db_read_write", "directed": True},
                        {"id": "e7", "source": "n4", "target": "n7", "label": "OrderPlaced event", "edge_type": "pub_sub", "directed": True},
                        {"id": "e8", "source": "n4", "target": "n8", "label": "process payment", "edge_type": "rpc_call", "directed": True},
                        {"id": "e9", "source": "n8", "target": "n9", "label": "authorize charge", "edge_type": "http_request", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"client": "React SPA Frontend", "gateway": "Kong API Gateway", "catalog_service": "Product Catalog Service", "order_service": "Order Processing Service", "cache": "Redis Cache", "database": "PostgreSQL Database", "message_broker": "Apache Kafka", "payment_service": "Payment Service", "payment_gateway": "Stripe Gateway"},
                {"client": "iOS & Android Apps", "gateway": "AWS API Gateway", "catalog_service": "Inventory Service", "order_service": "Checkout Service", "cache": "ElastiCache Memcached", "database": "Amazon Aurora MySQL", "message_broker": "RabbitMQ", "payment_service": "Billing Service", "payment_gateway": "PayPal SDK"}
            ]
        },
        {
            "template_id": "arch_ai_rag_pipeline",
            "domain": "artificial_intelligence",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Architecture of a generative AI pipeline: Users interact with {v['ui']}. Queries are sent to {v['api_server']}. The server generates embeddings via {v['embed_model']} and retrieves relevant context from {v['vector_db']}. Context and prompt are sent to {v['llm_service']}, which streams completions back to the user.",
                    "nodes": [
                        {"id": "n1", "label": v["ui"], "type": "client"},
                        {"id": "n2", "label": v["api_server"], "type": "service"},
                        {"id": "n3", "label": v["embed_model"], "type": "service"},
                        {"id": "n4", "label": v["vector_db"], "type": "database"},
                        {"id": "n5", "label": v["llm_service"], "type": "external_system"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "submit query", "edge_type": "http_request", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "generate vector", "edge_type": "rpc_call", "directed": True},
                        {"id": "e3", "source": "n2", "target": "n4", "label": "cosine search", "edge_type": "db_read_write", "directed": True},
                        {"id": "e4", "source": "n2", "target": "n5", "label": "augmented prompt", "edge_type": "http_request", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n2", "label": "stream token", "edge_type": "http_request", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"ui": "Chatbot Web Interface", "api_server": "FastAPI Backend Server", "embed_model": "Text-Embedding-3 Service", "vector_db": "Pinecone Vector Store", "llm_service": "Anthropic Claude API"},
                {"ui": "Enterprise Search Desktop", "api_server": "Node.js Express Server", "embed_model": "Hugging Face MiniLM Worker", "vector_db": "Qdrant Cluster", "llm_service": "OpenAI GPT-4o Service"}
            ]
        },
        {
            "template_id": "arch_realtime_iot_telemetry",
            "domain": "iot",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Architecture for real-time IoT processing: {v['iot_devices']} publish telemetry over MQTT to {v['broker']}. {v['ingestion_service']} consumes the queue, validates packets, and writes hot records to {v['ts_db']}. Downstream {v['analytics_engine']} computes aggregations and alerts {v['dashboard']} in real time.",
                    "nodes": [
                        {"id": "n1", "label": v["iot_devices"], "type": "client"},
                        {"id": "n2", "label": v["broker"], "type": "message_broker"},
                        {"id": "n3", "label": v["ingestion_service"], "type": "service"},
                        {"id": "n4", "label": v["ts_db"], "type": "database"},
                        {"id": "n5", "label": v["analytics_engine"], "type": "service"},
                        {"id": "n6", "label": v["dashboard"], "type": "client"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "MQTT publish", "edge_type": "pub_sub", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "queue consume", "edge_type": "pub_sub", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "append metrics", "edge_type": "db_read_write", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "stream window", "edge_type": "db_read_write", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n6", "label": "WebSocket telemetry", "edge_type": "http_request", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"iot_devices": "Edge Smart Sensors", "broker": "EMQX MQTT Broker", "ingestion_service": "Rust Telemetry Ingestion Worker", "ts_db": "TimescaleDB Database", "analytics_engine": "Apache Flink Engine", "dashboard": "Grafana Operations Board"},
                {"iot_devices": "Connected Vehicle Fleet", "broker": "AWS IoT Core", "ingestion_service": "Go Lambda Ingestor", "ts_db": "InfluxDB Cluster", "analytics_engine": "Spark Streaming Engine", "dashboard": "Fleet Command Center"}
            ]
        },
        {
            "template_id": "arch_banking_core_ledger",
            "domain": "fintech",
            "complexity": "complex",
            "generators": [
                lambda v: {
                    "text": f"Core banking ledger architecture: Mobile users connect through {v['api_gateway']}. Requests are authenticated by {v['auth_service']} and passed to {v['transaction_service']}. The transaction service reads and writes to {v['immutable_ledger']}. Fraud checks are performed asynchronously via {v['fraud_engine']} reading from {v['event_stream']}.",
                    "nodes": [
                        {"id": "n1", "label": "Banking Mobile Client", "type": "client"},
                        {"id": "n2", "label": v["api_gateway"], "type": "api_gateway"},
                        {"id": "n3", "label": v["auth_service"], "type": "service"},
                        {"id": "n4", "label": v["transaction_service"], "type": "service"},
                        {"id": "n5", "label": v["immutable_ledger"], "type": "database"},
                        {"id": "n6", "label": v["event_stream"], "type": "message_broker"},
                        {"id": "n7", "label": v["fraud_engine"], "type": "service"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "TLS mutual auth", "edge_type": "http_request", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "verify JWT", "edge_type": "rpc_call", "directed": True},
                        {"id": "e3", "source": "n2", "target": "n4", "label": "execute transfer", "edge_type": "rpc_call", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "ACID debit/credit", "edge_type": "db_read_write", "directed": True},
                        {"id": "e5", "source": "n4", "target": "n6", "label": "publish transaction", "edge_type": "pub_sub", "directed": True},
                        {"id": "e6", "source": "n6", "target": "n7", "label": "analyze anomaly", "edge_type": "pub_sub", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"api_gateway": "Apigee Gateway", "auth_service": "Keycloak Auth", "transaction_service": "Core Ledger Service", "immutable_ledger": "Amazon QLDB / PostgreSQL", "event_stream": "Kafka Financial Bus", "fraud_engine": "Realtime ML Scorer"},
                {"api_gateway": "Kong Enterprise Gateway", "auth_service": "OAuth Token Vault", "transaction_service": "Accounts Service", "immutable_ledger": "CockroachDB Cluster", "event_stream": "Pulsar Event Bus", "fraud_engine": "Risk Assessment Daemon"}
            ]
        },
        {
            "template_id": "arch_video_streaming_cdn",
            "domain": "media_streaming",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Video streaming architecture: Smart TV viewers stream video content from {v['cdn_edge']}. Cache misses at the edge fetch HLS video segments from {v['video_origin']}. Uploaded raw media is processed by {v['transcoder']} and stored in {v['object_store']}. Metadata and user profiles are queried from {v['metadata_db']}.",
                    "nodes": [
                        {"id": "n1", "label": "Smart TV & Web Players", "type": "client"},
                        {"id": "n2", "label": v["cdn_edge"], "type": "external_system"},
                        {"id": "n3", "label": v["video_origin"], "type": "service"},
                        {"id": "n4", "label": v["object_store"], "type": "database"},
                        {"id": "n5", "label": v["transcoder"], "type": "service"},
                        {"id": "n6", "label": v["metadata_db"], "type": "database"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "HLS chunk request", "edge_type": "http_request", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "origin pull", "edge_type": "http_request", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "fetch video blobs", "edge_type": "db_read_write", "directed": True},
                        {"id": "e4", "source": "n5", "target": "n4", "label": "save encoded profiles", "edge_type": "db_read_write", "directed": True},
                        {"id": "e5", "source": "n3", "target": "n6", "label": "read title metadata", "edge_type": "db_read_write", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"cdn_edge": "Cloudflare Global CDN", "video_origin": "Nginx Media Origin", "object_store": "AWS S3 Video Bucket", "transcoder": "FFmpeg Worker Cluster", "metadata_db": "ScyllaDB Metadata Store"},
                {"cdn_edge": "Fastly Edge Network", "video_origin": "Origin Shield Gateway", "object_store": "GCS Bucket Store", "transcoder": "AWS MediaConvert", "metadata_db": "DynamoDB Title Catalog"}
            ]
        }
    ]


def get_concept_map_templates() -> List[Dict[str, Any]]:
    return [
        {
            "template_id": "concept_data_structures_taxonomy",
            "domain": "computer_science",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Concept hierarchy for data structures: {v['root']} is divided into {v['cat_linear']} and {v['cat_nonlinear']}. {v['cat_linear']} data structures include {v['ds_array']}, {v['ds_list']}, and {v['ds_stack']}. {v['cat_nonlinear']} data structures include {v['ds_tree']} and {v['ds_graph']}. {v['ds_tree']} represents hierarchical structures while {v['ds_graph']} models arbitrary networks.",
                    "nodes": [
                        {"id": "n1", "label": v["root"], "type": "concept"},
                        {"id": "n2", "label": v["cat_linear"], "type": "category"},
                        {"id": "n3", "label": v["cat_nonlinear"], "type": "category"},
                        {"id": "n4", "label": v["ds_array"], "type": "concept"},
                        {"id": "n5", "label": v["ds_list"], "type": "concept"},
                        {"id": "n6", "label": v["ds_stack"], "type": "concept"},
                        {"id": "n7", "label": v["ds_tree"], "type": "concept"},
                        {"id": "n8", "label": v["ds_graph"], "type": "concept"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "classified as", "edge_type": "is_a", "directed": True},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "classified as", "edge_type": "is_a", "directed": True},
                        {"id": "e3", "source": "n2", "target": "n4", "label": "includes", "edge_type": "part_of", "directed": True},
                        {"id": "e4", "source": "n2", "target": "n5", "label": "includes", "edge_type": "part_of", "directed": True},
                        {"id": "e5", "source": "n2", "target": "n6", "label": "includes", "edge_type": "part_of", "directed": True},
                        {"id": "e6", "source": "n3", "target": "n7", "label": "includes", "edge_type": "part_of", "directed": True},
                        {"id": "e7", "source": "n3", "target": "n8", "label": "includes", "edge_type": "part_of", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"root": "Data Structures", "cat_linear": "Linear Structures", "cat_nonlinear": "Non-Linear Structures", "ds_array": "Array", "ds_list": "Linked List", "ds_stack": "Stack and Queue", "ds_tree": "Tree", "ds_graph": "Graph"},
                {"root": "Memory Collections", "cat_linear": "Sequential Memory", "cat_nonlinear": "Hierarchical & Linked Memory", "ds_array": "Contiguous Array", "ds_list": "Doubly Linked List", "ds_stack": "FIFO Queue", "ds_tree": "Binary Search Tree", "ds_graph": "Directed Acyclic Graph"}
            ]
        },
        {
            "template_id": "concept_machine_learning_paradigm",
            "domain": "machine_learning",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Machine Learning paradigms: {v['ml_root']} branches into {v['supervised']}, {v['unsupervised']}, and {v['reinforcement']}. {v['supervised']} relies on {v['labeled_data']} and includes {v['sup_algos']}. {v['unsupervised']} identifies patterns in {v['unlabeled_data']} using {v['unsup_algos']}. {v['reinforcement']} learns via rewards and penalties in an environment.",
                    "nodes": [
                        {"id": "n1", "label": v["ml_root"], "type": "concept"},
                        {"id": "n2", "label": v["supervised"], "type": "category"},
                        {"id": "n3", "label": v["unsupervised"], "type": "category"},
                        {"id": "n4", "label": v["reinforcement"], "type": "category"},
                        {"id": "n5", "label": v["labeled_data"], "type": "property"},
                        {"id": "n6", "label": v["sup_algos"], "type": "concept"},
                        {"id": "n7", "label": v["unlabeled_data"], "type": "property"},
                        {"id": "n8", "label": v["unsup_algos"], "type": "concept"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "paradigm of", "edge_type": "is_a", "directed": True},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "paradigm of", "edge_type": "is_a", "directed": True},
                        {"id": "e3", "source": "n1", "target": "n4", "label": "paradigm of", "edge_type": "is_a", "directed": True},
                        {"id": "e4", "source": "n2", "target": "n5", "label": "requires", "edge_type": "requires", "directed": True},
                        {"id": "e5", "source": "n2", "target": "n6", "label": "implemented by", "edge_type": "implements", "directed": True},
                        {"id": "e6", "source": "n3", "target": "n7", "label": "requires", "edge_type": "requires", "directed": True},
                        {"id": "e7", "source": "n3", "target": "n8", "label": "implemented by", "edge_type": "implements", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"ml_root": "Machine Learning", "supervised": "Supervised Learning", "unsupervised": "Unsupervised Learning", "reinforcement": "Reinforcement Learning", "labeled_data": "Ground-Truth Labeled Data", "sup_algos": "Classification and Regression Models", "unlabeled_data": "Unlabeled Raw Features", "unsup_algos": "Clustering and PCA"},
                {"ml_root": "Artificial Intelligence Modeling", "supervised": "Predictive Modeling", "unsupervised": "Descriptive Pattern Mining", "reinforcement": "Agent-Based Policy Learning", "labeled_data": "Annotated Training Examples", "sup_algos": "Support Vector Machines & Neural Nets", "unlabeled_data": "Unstructured Vector Space", "unsup_algos": "K-Means and t-SNE"}
            ]
        },
        {
            "template_id": "concept_operating_systems_kernel",
            "domain": "operating_systems",
            "complexity": "simple",
            "generators": [
                lambda v: {
                    "text": f"Operating System architecture: The {v['os_kernel']} provides core system services, managing {v['proc_mgmt']}, {v['mem_mgmt']}, and {v['file_system']}. {v['proc_mgmt']} schedules processes onto CPU cores. {v['mem_mgmt']} allocates virtual memory and paging. User applications communicate with the kernel through {v['syscall_interface']}.",
                    "nodes": [
                        {"id": "n1", "label": v["os_kernel"], "type": "concept"},
                        {"id": "n2", "label": v["proc_mgmt"], "type": "concept"},
                        {"id": "n3", "label": v["mem_mgmt"], "type": "concept"},
                        {"id": "n4", "label": v["file_system"], "type": "concept"},
                        {"id": "n5", "label": v["syscall_interface"], "type": "category"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "manages", "edge_type": "relates_to", "directed": True},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "manages", "edge_type": "relates_to", "directed": True},
                        {"id": "e3", "source": "n1", "target": "n4", "label": "manages", "edge_type": "relates_to", "directed": True},
                        {"id": "e4", "source": "n5", "target": "n1", "label": "interfaces with", "edge_type": "requires", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"os_kernel": "OS Kernel", "proc_mgmt": "Process Scheduler", "mem_mgmt": "Virtual Memory Manager", "file_system": "VFS File System", "syscall_interface": "POSIX System Call API"},
                {"os_kernel": "Monolithic Kernel Core", "proc_mgmt": "Thread Dispatcher", "mem_mgmt": "Page Frame Allocator", "file_system": "Storage Driver Layer", "syscall_interface": "System Trap Interface"}
            ]
        },
        {
            "template_id": "concept_database_models_taxonomy",
            "domain": "databases",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Database paradigms: {v['db_root']} is categorized into {v['sql_model']} and {v['nosql_model']}. {v['sql_model']} enforces {v['acid_prop']} and uses {v['relational_tables']}. {v['nosql_model']} includes {v['doc_store']}, {v['kv_store']}, and {v['graph_store']}. Graph databases specialize in highly interconnected network queries.",
                    "nodes": [
                        {"id": "n1", "label": v["db_root"], "type": "concept"},
                        {"id": "n2", "label": v["sql_model"], "type": "category"},
                        {"id": "n3", "label": v["nosql_model"], "type": "category"},
                        {"id": "n4", "label": v["acid_prop"], "type": "property"},
                        {"id": "n5", "label": v["relational_tables"], "type": "concept"},
                        {"id": "n6", "label": v["doc_store"], "type": "concept"},
                        {"id": "n7", "label": v["kv_store"], "type": "concept"},
                        {"id": "n8", "label": v["graph_store"], "type": "concept"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "family of", "edge_type": "is_a", "directed": True},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "family of", "edge_type": "is_a", "directed": True},
                        {"id": "e3", "source": "n2", "target": "n4", "label": "guarantees", "edge_type": "requires", "directed": True},
                        {"id": "e4", "source": "n2", "target": "n5", "label": "structures as", "edge_type": "implements", "directed": True},
                        {"id": "e5", "source": "n3", "target": "n6", "label": "includes", "edge_type": "part_of", "directed": True},
                        {"id": "e6", "source": "n3", "target": "n7", "label": "includes", "edge_type": "part_of", "directed": True},
                        {"id": "e7", "source": "n3", "target": "n8", "label": "includes", "edge_type": "part_of", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"db_root": "Database Management Systems", "sql_model": "Relational Databases", "nosql_model": "NoSQL Systems", "acid_prop": "ACID Consistency", "relational_tables": "Normalized SQL Tables", "doc_store": "Document Stores (MongoDB)", "kv_store": "Key-Value Caches (Redis)", "graph_store": "Graph Engines (Neo4j)"},
                {"db_root": "Data Persistence Architectures", "sql_model": "Structured SQL Engines", "nosql_model": "Distributed Non-Relational", "acid_prop": "Strict Serializability", "relational_tables": "Schema Tables & Foreign Keys", "doc_store": "JSON Document Collections", "kv_store": "In-Memory KV Pairs", "graph_store": "Property Graph Stores"}
            ]
        },
        {
            "template_id": "concept_network_osi_stack",
            "domain": "computer_networking",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"The {v['network_model']} arranges communication into layers: {v['app_layer']} serves end-user applications via {v['app_protocols']}. {v['transport_layer']} provides reliable delivery through {v['transport_protocols']}. {v['network_layer']} routes packets across networks using {v['ip_protocol']}. {v['datalink_layer']} frames data for physical transmission.",
                    "nodes": [
                        {"id": "n1", "label": v["network_model"], "type": "concept"},
                        {"id": "n2", "label": v["app_layer"], "type": "category"},
                        {"id": "n3", "label": v["transport_layer"], "type": "category"},
                        {"id": "n4", "label": v["network_layer"], "type": "category"},
                        {"id": "n5", "label": v["datalink_layer"], "type": "category"},
                        {"id": "n6", "label": v["app_protocols"], "type": "concept"},
                        {"id": "n7", "label": v["transport_protocols"], "type": "concept"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "top layer", "edge_type": "part_of", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "passes to", "edge_type": "relates_to", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "segments to", "edge_type": "relates_to", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "packets to", "edge_type": "relates_to", "directed": True},
                        {"id": "e5", "source": "n2", "target": "n6", "label": "implements", "edge_type": "implements", "directed": True},
                        {"id": "e6", "source": "n3", "target": "n7", "label": "implements", "edge_type": "implements", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"network_model": "OSI 7-Layer Protocol Reference Model", "app_layer": "Application Layer", "transport_layer": "Transport Layer", "network_layer": "Network Layer", "datalink_layer": "Data Link & Physical Layer", "app_protocols": "HTTP & DNS Protocols", "transport_protocols": "TCP and UDP Sockets", "ip_protocol": "IPv4 and IPv6 Routing"},
                {"network_model": "TCP/IP Networking Stack", "app_layer": "User Application Space", "transport_layer": "Host-to-Host Transport", "network_layer": "Internetwork Routing", "datalink_layer": "Ethernet MAC Framing", "app_protocols": "TLS & gRPC Payloads", "transport_protocols": "Reliable Stream Transmission", "ip_protocol": "IP Packet Forwarding"}
            ]
        }
    ]


def get_er_diagram_templates() -> List[Dict[str, Any]]:
    return [
        {
            "template_id": "er_university_management",
            "domain": "education_database",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Entity-relationship design for a university database: Each {v['student']} has a {v['student_id']} and belongs to exactly one {v['department']}. A {v['department']} offers multiple {v['course']} entities. Each {v['student']} can enroll in multiple {v['course']} records, and each {v['course']} has multiple students. {v['instructor']} entities teach {v['course']} offerings.",
                    "nodes": [
                        {"id": "n1", "label": v["student"], "type": "entity"},
                        {"id": "n2", "label": v["department"], "type": "entity"},
                        {"id": "n3", "label": v["course"], "type": "entity"},
                        {"id": "n4", "label": v["instructor"], "type": "entity"},
                        {"id": "n5", "label": v["student_id"], "type": "key_attribute"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n5", "label": "has key", "edge_type": "has_attribute", "directed": False},
                        {"id": "e2", "source": "n1", "target": "n2", "label": "belongs to (N:1)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e3", "source": "n2", "target": "n3", "label": "offers (1:N)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e4", "source": "n1", "target": "n3", "label": "enrolls in (M:N)", "edge_type": "many_to_many", "directed": False},
                        {"id": "e5", "source": "n4", "target": "n3", "label": "teaches (1:N)", "edge_type": "one_to_many", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"student": "Student", "student_id": "student_roll_no (PK)", "department": "Department", "course": "Course", "instructor": "Professor"},
                {"student": "Undergraduate Scholar", "student_id": "scholar_id (PK)", "department": "Academic Faculty", "course": "Class Module", "instructor": "Lecturer"}
            ]
        },
        {
            "template_id": "er_hospital_patient_system",
            "domain": "healthcare_database",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Hospital database entity-relationship schema: {v['patient']} has primary key {v['patient_id']} and medical history. Each {v['patient']} is assigned to one {v['ward']}. {v['doctor']} treats multiple {v['patient']} cases. A {v['doctor']} writes multiple {v['prescription']} records, and each {v['prescription']} is linked to one {v['patient']}.",
                    "nodes": [
                        {"id": "n1", "label": v["patient"], "type": "entity"},
                        {"id": "n2", "label": v["patient_id"], "type": "key_attribute"},
                        {"id": "n3", "label": v["ward"], "type": "entity"},
                        {"id": "n4", "label": v["doctor"], "type": "entity"},
                        {"id": "n5", "label": v["prescription"], "type": "entity"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "primary key", "edge_type": "has_attribute", "directed": False},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "admitted to (N:1)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e3", "source": "n4", "target": "n1", "label": "treats (1:N)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "issues (1:N)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n1", "label": "prescribed for (N:1)", "edge_type": "one_to_many", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"patient": "Patient", "patient_id": "patient_mrn (PK)", "ward": "Hospital Ward", "doctor": "Attending Physician", "prescription": "Medication Order"},
                {"patient": "Inpatient Record", "patient_id": "admission_no (PK)", "ward": "Clinical Unit", "doctor": "Medical Specialist", "prescription": "Prescription Plan"}
            ]
        },
        {
            "template_id": "er_ecommerce_orders_schema",
            "domain": "commerce_database",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Entity-relationship diagram for an e-commerce database: {v['customer']} has primary key {v['cust_pk']} and places multiple {v['order']} entities. Each {v['order']} contains multiple {v['order_item']} rows. Each {v['order_item']} references one {v['product']}. Each {v['product']} belongs to a {v['category']}.",
                    "nodes": [
                        {"id": "n1", "label": v["customer"], "type": "entity"},
                        {"id": "n2", "label": v["cust_pk"], "type": "key_attribute"},
                        {"id": "n3", "label": v["order"], "type": "entity"},
                        {"id": "n4", "label": v["order_item"], "type": "entity"},
                        {"id": "n5", "label": v["product"], "type": "entity"},
                        {"id": "n6", "label": v["category"], "type": "entity"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "primary key", "edge_type": "has_attribute", "directed": False},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "places (1:N)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "contains (1:N)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "references (N:1)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n6", "label": "categorized in (N:1)", "edge_type": "one_to_many", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"customer": "Customer Account", "cust_pk": "customer_id (PK)", "order": "Customer Order", "order_item": "Line Item", "product": "Product SKU", "category": "Product Category"},
                {"customer": "Registered Buyer", "cust_pk": "buyer_uuid (PK)", "order": "Purchase Invoice", "order_item": "Invoice Item", "product": "Catalog Item", "category": "Department"}
            ]
        },
        {
            "template_id": "er_airline_reservation_db",
            "domain": "aviation_database",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Airline reservation database: {v['passenger']} holds primary key {v['pass_id']} and creates multiple {v['booking']} records. A {v['booking']} reserves a seat on a specific {v['flight']}. Each {v['flight']} departs from an origin {v['airport']} and arrives at a destination {v['airport']}.",
                    "nodes": [
                        {"id": "n1", "label": v["passenger"], "type": "entity"},
                        {"id": "n2", "label": v["pass_id"], "type": "key_attribute"},
                        {"id": "n3", "label": v["booking"], "type": "entity"},
                        {"id": "n4", "label": v["flight"], "type": "entity"},
                        {"id": "n5", "label": v["airport"], "type": "entity"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "primary key", "edge_type": "has_attribute", "directed": False},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "books (1:N)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "reserves seat on (N:1)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "routes between (N:M)", "edge_type": "many_to_many", "directed": False}
                    ]
                }
            ],
            "param_sets": [
                {"passenger": "Airline Passenger", "pass_id": "passport_number (PK)", "booking": "Flight Reservation", "flight": "Scheduled Flight", "airport": "Airport Hub"},
                {"passenger": "Traveler Profile", "pass_id": "frequent_flyer_id (PK)", "booking": "Ticket Itinerary", "flight": "Commercial Route", "airport": "Terminal Station"}
            ]
        },
        {
            "template_id": "er_library_circulation_db",
            "domain": "library_database",
            "complexity": "simple",
            "generators": [
                lambda v: {
                    "text": f"Library database ER model: A {v['book']} has ISBN {v['isbn_pk']} and is written by one or more {v['author']} entities. A {v['member']} borrows multiple {v['book']} copies through {v['loan']} transactions. Each {v['loan']} tracks issue and due dates.",
                    "nodes": [
                        {"id": "n1", "label": v["book"], "type": "entity"},
                        {"id": "n2", "label": v["isbn_pk"], "type": "key_attribute"},
                        {"id": "n3", "label": v["author"], "type": "entity"},
                        {"id": "n4", "label": v["member"], "type": "entity"},
                        {"id": "n5", "label": v["loan"], "type": "entity"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "primary key", "edge_type": "has_attribute", "directed": False},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "written by (M:N)", "edge_type": "many_to_many", "directed": False},
                        {"id": "e3", "source": "n4", "target": "n5", "label": "initiates (1:N)", "edge_type": "one_to_many", "directed": True},
                        {"id": "e4", "source": "n5", "target": "n1", "label": "borrows (N:1)", "edge_type": "one_to_many", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"book": "Library Book", "isbn_pk": "isbn_code (PK)", "author": "Book Author", "member": "Library Cardholder", "loan": "Checkout Loan Record"},
                {"book": "Academic Monograph", "isbn_pk": "catalog_call_no (PK)", "author": "Research Scholar", "member": "University Patron", "loan": "Circulation Slip"}
            ]
        }
    ]


def get_sequence_diagram_templates() -> List[Dict[str, Any]]:
    return [
        {
            "template_id": "seq_user_checkout_payment",
            "domain": "finance",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Sequence of interactions during payment checkout: {v['customer']} submits checkout details to {v['frontend']}. {v['frontend']} sends a POST order request to {v['order_service']}. {v['order_service']} requests payment authorization from {v['payment_gateway']}. {v['payment_gateway']} queries {v['bank']} and receives confirmation. {v['payment_gateway']} returns success token to {v['order_service']}. {v['order_service']} notifies {v['frontend']}, which displays confirmation to {v['customer']}.",
                    "nodes": [
                        {"id": "n1", "label": v["customer"], "type": "actor"},
                        {"id": "n2", "label": v["frontend"], "type": "participant"},
                        {"id": "n3", "label": v["order_service"], "type": "participant"},
                        {"id": "n4", "label": v["payment_gateway"], "type": "participant"},
                        {"id": "n5", "label": v["bank"], "type": "participant"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "1. Click Checkout", "edge_type": "sync_call", "directed": True, "metadata": {"order": 1}},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "2. POST /orders", "edge_type": "sync_call", "directed": True, "metadata": {"order": 2}},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "3. AuthorizeCharge()", "edge_type": "sync_call", "directed": True, "metadata": {"order": 3}},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "4. VerifyFunds()", "edge_type": "sync_call", "directed": True, "metadata": {"order": 4}},
                        {"id": "e5", "source": "n5", "target": "n4", "label": "5. FundsApproved", "edge_type": "return_value", "directed": True, "metadata": {"order": 5}},
                        {"id": "e6", "source": "n4", "target": "n3", "label": "6. PaymentSuccessToken", "edge_type": "return_value", "directed": True, "metadata": {"order": 6}},
                        {"id": "e7", "source": "n3", "target": "n2", "label": "7. OrderConfirmedResponse", "edge_type": "return_value", "directed": True, "metadata": {"order": 7}},
                        {"id": "e8", "source": "n2", "target": "n1", "label": "8. Display Success Screen", "edge_type": "return_value", "directed": True, "metadata": {"order": 8}}
                    ]
                }
            ],
            "param_sets": [
                {"customer": "Customer", "frontend": "Web Storefront", "order_service": "Order Service", "payment_gateway": "Stripe Gateway", "bank": "Card Issuing Bank"},
                {"customer": "Shopper App", "frontend": "Mobile Client", "order_service": "Commerce API", "payment_gateway": "PayPal SDK", "bank": "Visa Network"}
            ]
        },
        {
            "template_id": "seq_oauth2_authorization",
            "domain": "security_protocols",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Sequence diagram for OAuth 2.0 authorization code flow: {v['client_app']} redirects {v['resource_owner']} to {v['auth_server']} login page. {v['resource_owner']} provides credentials and grants consent. {v['auth_server']} redirects back to {v['client_app']} with an authorization code. {v['client_app']} exchanges the authorization code with {v['auth_server']} for an access token. {v['client_app']} accesses {v['resource_server']} using the bearer token.",
                    "nodes": [
                        {"id": "n1", "label": v["resource_owner"], "type": "actor"},
                        {"id": "n2", "label": v["client_app"], "type": "participant"},
                        {"id": "n3", "label": v["auth_server"], "type": "participant"},
                        {"id": "n4", "label": v["resource_server"], "type": "participant"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n2", "target": "n1", "label": "1. Redirect to Auth", "edge_type": "sync_call", "directed": True, "metadata": {"order": 1}},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "2. Submit Login & Consent", "edge_type": "sync_call", "directed": True, "metadata": {"order": 2}},
                        {"id": "e3", "source": "n3", "target": "n2", "label": "3. AuthCode Redirect", "edge_type": "return_value", "directed": True, "metadata": {"order": 3}},
                        {"id": "e4", "source": "n2", "target": "n3", "label": "4. POST /token (code)", "edge_type": "sync_call", "directed": True, "metadata": {"order": 4}},
                        {"id": "e5", "source": "n3", "target": "n2", "label": "5. Return AccessToken", "edge_type": "return_value", "directed": True, "metadata": {"order": 5}},
                        {"id": "e6", "source": "n2", "target": "n4", "label": "6. GET /api (Bearer Token)", "edge_type": "sync_call", "directed": True, "metadata": {"order": 6}}
                    ]
                }
            ],
            "param_sets": [
                {"resource_owner": "User Browser", "client_app": "Third-Party App", "auth_server": "Google OAuth Server", "resource_server": "Google Drive API"},
                {"resource_owner": "Employee Client", "client_app": "Internal Analytics Portal", "auth_server": "Okta Identity Provider", "resource_server": "HR REST Service"}
            ]
        },
        {
            "template_id": "seq_rideshare_dispatch_flow",
            "domain": "transportation",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Ride sharing sequence: A {v['passenger']} requests a ride on their phone. The {v['dispatch_server']} queries nearby {v['driver']} units. The nearest {v['driver']} accepts the ride offer. The {v['dispatch_server']} locks the reservation and streams the driver's real-time ETA back to the {v['passenger']}.",
                    "nodes": [
                        {"id": "n1", "label": v["passenger"], "type": "actor"},
                        {"id": "n2", "label": v["dispatch_server"], "type": "participant"},
                        {"id": "n3", "label": v["driver"], "type": "participant"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "1. RequestRide(pickup, dest)", "edge_type": "sync_call", "directed": True, "metadata": {"order": 1}},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "2. DispatchOffer(route)", "edge_type": "sync_call", "directed": True, "metadata": {"order": 2}},
                        {"id": "e3", "source": "n3", "target": "n2", "label": "3. AcceptOffer(driver_id)", "edge_type": "return_value", "directed": True, "metadata": {"order": 3}},
                        {"id": "e4", "source": "n2", "target": "n1", "label": "4. StreamDriverETA()", "edge_type": "return_value", "directed": True, "metadata": {"order": 4}}
                    ]
                }
            ],
            "param_sets": [
                {"passenger": "Rider Passenger", "dispatch_server": "Ride Matching Engine", "driver": "Nearest Driver Vehicle"},
                {"passenger": "Commuter", "dispatch_server": "Cab Dispatch Dispatcher", "driver": "Taxi Operator"}
            ]
        },
        {
            "template_id": "seq_two_factor_auth_flow",
            "domain": "security",
            "complexity": "simple",
            "generators": [
                lambda v: {
                    "text": f"Two-factor authentication sequence: User submits credentials to {v['auth_service']}. {v['auth_service']} generates an OTP and commands {v['sms_gateway']} to dispatch an SMS to {v['user_phone']}. User enters OTP on the web form. {v['auth_service']} validates the OTP and issues a session cookie.",
                    "nodes": [
                        {"id": "n1", "label": "User", "type": "actor"},
                        {"id": "n2", "label": v["auth_service"], "type": "participant"},
                        {"id": "n3", "label": v["sms_gateway"], "type": "participant"},
                        {"id": "n4", "label": v["user_phone"], "type": "participant"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "1. PostCredentials()", "edge_type": "sync_call", "directed": True, "metadata": {"order": 1}},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "2. SendSMS(otp_code)", "edge_type": "sync_call", "directed": True, "metadata": {"order": 2}},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "3. DeliverSMSMessage()", "edge_type": "async_message", "directed": True, "metadata": {"order": 3}},
                        {"id": "e4", "source": "n1", "target": "n2", "label": "4. SubmitOTP(code)", "edge_type": "sync_call", "directed": True, "metadata": {"order": 4}},
                        {"id": "e5", "source": "n2", "target": "n1", "label": "5. SessionGranted(cookie)", "edge_type": "return_value", "directed": True, "metadata": {"order": 5}}
                    ]
                }
            ],
            "param_sets": [
                {"auth_service": "Enterprise SSO Gateway", "sms_gateway": "Twilio SMS Service", "user_phone": "Mobile Phone Handset"},
                {"auth_service": "Banking Auth Portal", "sms_gateway": "Telephony Carrier Gateway", "user_phone": "Customer Smartphone"}
            ]
        },
        {
            "template_id": "seq_microservice_saga_order",
            "domain": "distributed_transactions",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Saga choreography sequence: {v['order_orch']} sends reserve command to {v['inv_service']}. The inventory service confirms inventory held. Then {v['order_orch']} calls {v['pay_service']}. If payment succeeds, {v['order_orch']} signals {v['ship_service']} to schedule delivery.",
                    "nodes": [
                        {"id": "n1", "label": v["order_orch"], "type": "participant"},
                        {"id": "n2", "label": v["inv_service"], "type": "participant"},
                        {"id": "n3", "label": v["pay_service"], "type": "participant"},
                        {"id": "n4", "label": v["ship_service"], "type": "participant"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "1. ReserveInventory(sku)", "edge_type": "sync_call", "directed": True, "metadata": {"order": 1}},
                        {"id": "e2", "source": "n2", "target": "n1", "label": "2. InventoryReservedOK", "edge_type": "return_value", "directed": True, "metadata": {"order": 2}},
                        {"id": "e3", "source": "n1", "target": "n3", "label": "3. ChargePayment(amount)", "edge_type": "sync_call", "directed": True, "metadata": {"order": 3}},
                        {"id": "e4", "source": "n3", "target": "n1", "label": "4. PaymentChargedOK", "edge_type": "return_value", "directed": True, "metadata": {"order": 4}},
                        {"id": "e5", "source": "n1", "target": "n4", "label": "5. DispatchOrder(order_id)", "edge_type": "async_message", "directed": True, "metadata": {"order": 5}}
                    ]
                }
            ],
            "param_sets": [
                {"order_orch": "Order Saga Orchestrator", "inv_service": "Warehouse Inventory Service", "pay_service": "Billing Payment Service", "ship_service": "Logistics Dispatch Service"},
                {"order_orch": "Temporal Workflow Coordinator", "inv_service": "Stock Service", "pay_service": "Credit Card Gateway", "ship_service": "Courier Integration Service"}
            ]
        }
    ]


def get_network_topology_templates() -> List[Dict[str, Any]]:
    return [
        {
            "template_id": "net_office_lan_wan",
            "domain": "networking",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Network topology for {v['office_name']}: Several {v['workstations']} connect via Ethernet to access switch {v['switch']}. The switch connects to core router {v['router']}. The router passes through perimeter firewall {v['firewall']} to establish connection to the public {v['internet']}. An internal {v['server']} is connected to the core router.",
                    "nodes": [
                        {"id": "n1", "label": v["workstations"], "type": "workstation"},
                        {"id": "n2", "label": v["switch"], "type": "switch"},
                        {"id": "n3", "label": v["router"], "type": "router"},
                        {"id": "n4", "label": v["server"], "type": "server"},
                        {"id": "n5", "label": v["firewall"], "type": "firewall"},
                        {"id": "n6", "label": v["internet"], "type": "internet"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "Gigabit Ethernet", "edge_type": "ethernet", "directed": False},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "Trunk Link", "edge_type": "ethernet", "directed": False},
                        {"id": "e3", "source": "n4", "target": "n3", "label": "Server VLAN", "edge_type": "ethernet", "directed": False},
                        {"id": "e4", "source": "n3", "target": "n5", "label": "WAN Interface", "edge_type": "wan_link", "directed": False},
                        {"id": "e5", "source": "n5", "target": "n6", "label": "BGP ISP Transit", "edge_type": "wan_link", "directed": False}
                    ]
                }
            ],
            "param_sets": [
                {"office_name": "Regional Branch Office", "workstations": "Client PC Workstations", "switch": "Cisco Catalyst Switch", "router": "Branch Edge Router", "server": "Local File & Print Server", "firewall": "Fortinet Perimeter Firewall", "internet": "Internet Transit"},
                {"office_name": "Engineering Headquarters", "workstations": "Developer Laptops", "switch": "Aruba 48-Port Switch", "router": "Core Juniper Gateway", "server": "Local GitLab Runner", "firewall": "Palo Alto NGFW", "internet": "Public Fiber WAN"}
            ]
        },
        {
            "template_id": "net_dmz_datacenter",
            "domain": "security_infrastructure",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Datacenter DMZ topology: Incoming internet traffic enters through {v['external_firewall']}. It is distributed by {v['load_balancer']} to public {v['web_servers']} located inside the DMZ. Traffic from the DMZ must traverse {v['internal_firewall']} to reach private {v['db_cluster']} in the secure internal zone.",
                    "nodes": [
                        {"id": "n1", "label": "Public Internet", "type": "internet"},
                        {"id": "n2", "label": v["external_firewall"], "type": "firewall"},
                        {"id": "n3", "label": v["load_balancer"], "type": "router"},
                        {"id": "n4", "label": v["web_servers"], "type": "server"},
                        {"id": "n5", "label": v["internal_firewall"], "type": "firewall"},
                        {"id": "n6", "label": v["db_cluster"], "type": "server"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "Inbound 443", "edge_type": "wan_link", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "Filtered Ingress", "edge_type": "ethernet", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "Balanced Pool", "edge_type": "ethernet", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "Internal Query", "edge_type": "ethernet", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n6", "label": "Port 5432 Only", "edge_type": "ethernet", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"external_firewall": "Edge Screening Firewall", "load_balancer": "F5 BIG-IP Load Balancer", "web_servers": "Nginx DMZ Web Nodes", "internal_firewall": "Zero-Trust Internal Firewall", "db_cluster": "Internal Database Cluster"},
                {"external_firewall": "AWS Network Firewall", "load_balancer": "Application Load Balancer", "web_servers": "ECS Web Containers", "internal_firewall": "Security Group Gateway", "db_cluster": "Private Aurora Cluster"}
            ]
        },
        {
            "template_id": "net_hybrid_cloud_vpn",
            "domain": "cloud_networking",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Hybrid cloud network diagram: On-premises datacenter connects via {v['vpn_device']} over an encrypted IPsec tunnel to {v['cloud_gateway']}. The cloud gateway routes into {v['private_subnet']} hosting internal {v['app_servers']}, which query {v['managed_db']}.",
                    "nodes": [
                        {"id": "n1", "label": "On-Premises Datacenter", "type": "server"},
                        {"id": "n2", "label": v["vpn_device"], "type": "router"},
                        {"id": "n3", "label": v["cloud_gateway"], "type": "router"},
                        {"id": "n4", "label": v["private_subnet"], "type": "switch"},
                        {"id": "n5", "label": v["app_servers"], "type": "server"},
                        {"id": "n6", "label": v["managed_db"], "type": "server"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "Local LAN", "edge_type": "ethernet", "directed": False},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "IPsec VPN Tunnel", "edge_type": "vpn_tunnel", "directed": False},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "Transit Route", "edge_type": "ethernet", "directed": False},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "VPC Peering", "edge_type": "ethernet", "directed": False},
                        {"id": "e5", "source": "n5", "target": "n6", "label": "Database Connection", "edge_type": "ethernet", "directed": False}
                    ]
                }
            ],
            "param_sets": [
                {"vpn_device": "Cisco ASA VPN Appliance", "cloud_gateway": "AWS Transit Gateway", "private_subnet": "Private App Subnet", "app_servers": "EC2 Microservice Instances", "managed_db": "RDS Postgres Multi-AZ"},
                {"vpn_device": "Palo Alto IPSec Gateway", "cloud_gateway": "Azure Virtual Network Gateway", "private_subnet": "VNet Private Tier", "app_servers": "Azure VM Scale Set", "managed_db": "Azure SQL Managed Instance"}
            ]
        },
        {
            "template_id": "net_campus_three_tier",
            "domain": "enterprise_networking",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Campus hierarchical network: User devices connect to {v['access_switch']}. The access switches uplink redundantly to {v['distribution_switch']}. Distribution switches connect to high-speed {v['core_switch']}, which interfaces with {v['edge_router']} for campus internet routing.",
                    "nodes": [
                        {"id": "n1", "label": "End-User Laptops & Phones", "type": "workstation"},
                        {"id": "n2", "label": v["access_switch"], "type": "switch"},
                        {"id": "n3", "label": v["distribution_switch"], "type": "switch"},
                        {"id": "n4", "label": v["core_switch"], "type": "switch"},
                        {"id": "n5", "label": v["edge_router"], "type": "router"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "Access 1GbE", "edge_type": "ethernet", "directed": False},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "Dual 10GbE Uplink", "edge_type": "ethernet", "directed": False},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "40GbE Fiber Backbone", "edge_type": "fiber", "directed": False},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "100GbE Transit", "edge_type": "fiber", "directed": False}
                    ]
                }
            ],
            "param_sets": [
                {"access_switch": "Building Access Switches", "distribution_switch": "Floor Aggregation Switches", "core_switch": "Campus Core Chassis Switch", "edge_router": "Border BGP Gateway Router"},
                {"access_switch": "PoE Edge Switches", "distribution_switch": "Distribution Multi-Layer Switches", "core_switch": "Enterprise Core Switch", "edge_router": "External Firewall Router"}
            ]
        },
        {
            "template_id": "net_sdwan_branch_fabric",
            "domain": "telecommunications",
            "complexity": "simple",
            "generators": [
                lambda v: {
                    "text": f"SD-WAN branch deployment: Remote branch devices link to {v['sdwan_edge']}. The edge device establishes dynamic overlays over dual transports: {v['mpls_circuit']} for critical traffic and {v['broadband']} for general cloud access, orchestrated by central {v['sdwan_ctrl']}.",
                    "nodes": [
                        {"id": "n1", "label": "Branch LAN Clients", "type": "workstation"},
                        {"id": "n2", "label": v["sdwan_edge"], "type": "router"},
                        {"id": "n3", "label": v["mpls_circuit"], "type": "internet"},
                        {"id": "n4", "label": v["broadband"], "type": "internet"},
                        {"id": "n5", "label": v["sdwan_ctrl"], "type": "server"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "LAN Access", "edge_type": "ethernet", "directed": False},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "MPLS SLA Path", "edge_type": "wan_link", "directed": False},
                        {"id": "e3", "source": "n2", "target": "n4", "label": "Commodity Broadband", "edge_type": "wan_link", "directed": False},
                        {"id": "e4", "source": "n2", "target": "n5", "label": "Control Plane Telemetry", "edge_type": "vpn_tunnel", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"sdwan_edge": "Cisco Catalyst 8000 SD-WAN Edge", "mpls_circuit": "Private MPLS Network", "broadband": "Commercial Fiber Internet", "sdwan_ctrl": "vManage Cloud Controller"},
                {"sdwan_edge": "FortiGate Secure SD-WAN", "mpls_circuit": "Metro Ethernet Line", "broadband": "Direct Internet Access (DIA)", "sdwan_ctrl": "FortiManager Orchestrator"}
            ]
        }
    ]


def get_dependency_graph_templates() -> List[Dict[str, Any]]:
    return [
        {
            "template_id": "dep_software_dev_lifecycle",
            "domain": "project_management",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Software development task dependencies: Project kicks off with {v['req_gathering']}. Once requirements are finalized, {v['frontend_dev']} and {v['backend_dev']} can proceed in parallel. Both frontend and backend tasks must be complete before {v['integration']} begins. Following integration, {v['qa_testing']} is executed. Finally, passing QA allows {v['deployment']}.",
                    "nodes": [
                        {"id": "n1", "label": v["req_gathering"], "type": "task"},
                        {"id": "n2", "label": v["frontend_dev"], "type": "task"},
                        {"id": "n3", "label": v["backend_dev"], "type": "task"},
                        {"id": "n4", "label": v["integration"], "type": "task"},
                        {"id": "n5", "label": v["qa_testing"], "type": "task"},
                        {"id": "n6", "label": v["deployment"], "type": "milestone"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "prerequisite for", "edge_type": "depends_on", "directed": True},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "prerequisite for", "edge_type": "depends_on", "directed": True},
                        {"id": "e3", "source": "n2", "target": "n4", "label": "depends on", "edge_type": "depends_on", "directed": True},
                        {"id": "e4", "source": "n3", "target": "n4", "label": "depends on", "edge_type": "depends_on", "directed": True},
                        {"id": "e5", "source": "n4", "target": "n5", "label": "triggers", "edge_type": "depends_on", "directed": True},
                        {"id": "e6", "source": "n5", "target": "n6", "label": "enables", "edge_type": "depends_on", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"req_gathering": "Requirements & Architecture Spec", "frontend_dev": "React UI Component Development", "backend_dev": "REST API Microservice Implementation", "integration": "System Integration & Contract Testing", "qa_testing": "Automated End-to-End Regression", "deployment": "Production Release Deployment"},
                {"req_gathering": "User Story Definition", "frontend_dev": "Flutter Mobile Screen Coding", "backend_dev": "GraphQL Server Endpoint Setup", "integration": "Client-Server API Integration", "qa_testing": "User Acceptance Testing (UAT)", "deployment": "App Store Distribution"}
            ]
        },
        {
            "template_id": "dep_cicd_build_pipeline",
            "domain": "devops_pipelines",
            "complexity": "simple",
            "generators": [
                lambda v: {
                    "text": f"CI/CD build pipeline dependencies: Code checkout triggers {v['lint_task']} and {v['unit_test']}. Building {v['container_build']} depends on passing both unit tests and linter. Once the container is built, {v['sec_scan']} runs. If security scans pass, deploy to {v['staging_env']}.",
                    "nodes": [
                        {"id": "n1", "label": "Source Code Checkout", "type": "milestone"},
                        {"id": "n2", "label": v["lint_task"], "type": "task"},
                        {"id": "n3", "label": v["unit_test"], "type": "task"},
                        {"id": "n4", "label": v["container_build"], "type": "task"},
                        {"id": "n5", "label": v["sec_scan"], "type": "task"},
                        {"id": "n6", "label": v["staging_env"], "type": "milestone"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "triggers", "edge_type": "depends_on", "directed": True},
                        {"id": "e2", "source": "n1", "target": "n3", "label": "triggers", "edge_type": "depends_on", "directed": True},
                        {"id": "e3", "source": "n2", "target": "n4", "label": "blocks", "edge_type": "depends_on", "directed": True},
                        {"id": "e4", "source": "n3", "target": "n4", "label": "blocks", "edge_type": "depends_on", "directed": True},
                        {"id": "e5", "source": "n4", "target": "n5", "label": "produces image for", "edge_type": "depends_on", "directed": True},
                        {"id": "e6", "source": "n5", "target": "n6", "label": "approves", "edge_type": "depends_on", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"lint_task": "Static Code Analysis (ESLint/Flake8)", "unit_test": "PyTest Unit Tests", "container_build": "Docker Image Build", "sec_scan": "Trivy Container Vulnerability Scan", "staging_env": "Kubernetes Staging Deployment"},
                {"lint_task": "SonarQube Quality Gate", "unit_test": "JUnit Test Suite", "container_build": "OCI Container Assembly", "sec_scan": "Snyk Dependency Audit", "staging_env": "AWS ECS Staging Environment"}
            ]
        },
        {
            "template_id": "dep_ml_pipeline_lifecycle",
            "domain": "mlops",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Machine learning training workflow dependencies: Raw data extraction precedes {v['cleaning_step']}. {v['feature_eng']} depends on cleaned data. {v['model_train']} requires engineered features. Once trained, {v['model_eval']} assesses benchmark metrics. Only when evaluation passes the accuracy threshold can {v['model_deploy']} proceed.",
                    "nodes": [
                        {"id": "n1", "label": "Data Extraction", "type": "task"},
                        {"id": "n2", "label": v["cleaning_step"], "type": "task"},
                        {"id": "n3", "label": v["feature_eng"], "type": "task"},
                        {"id": "n4", "label": v["model_train"], "type": "task"},
                        {"id": "n5", "label": v["model_eval"], "type": "task"},
                        {"id": "n6", "label": v["model_deploy"], "type": "milestone"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "feeds into", "edge_type": "depends_on", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "prerequisite", "edge_type": "depends_on", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "input for", "edge_type": "depends_on", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "evaluates", "edge_type": "depends_on", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n6", "label": "promotes", "edge_type": "depends_on", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"cleaning_step": "Outlier Detection & Imputation", "feature_eng": "TF-IDF & Embedding Vectorization", "model_train": "Gradient Boosted Trees Training", "model_eval": "Held-Out Test Set Evaluation", "model_deploy": "Triton Model Server Deployment"},
                {"cleaning_step": "Data Deduplication & Schema Check", "feature_eng": "Standardization & Normalization", "model_train": "Deep Neural Network Epochs", "model_eval": "F1-Score and Latency Profiling", "model_deploy": "Production Canary Endpoint Rollout"}
            ]
        },
        {
            "template_id": "dep_compiler_pipeline",
            "domain": "compilers",
            "complexity": "medium",
            "generators": [
                lambda v: {
                    "text": f"Compiler build pipeline dependencies: Source code is first tokenized by {v['lexer']}. {v['parser']} depends on the token stream to construct the AST. {v['semantic_analyzer']} validates types on the AST. {v['optimizer']} transforms the validated intermediate representation. Finally, {v['code_generator']} produces target machine assembly.",
                    "nodes": [
                        {"id": "n1", "label": "Source Code Text", "type": "task"},
                        {"id": "n2", "label": v["lexer"], "type": "task"},
                        {"id": "n3", "label": v["parser"], "type": "task"},
                        {"id": "n4", "label": v["semantic_analyzer"], "type": "task"},
                        {"id": "n5", "label": v["optimizer"], "type": "task"},
                        {"id": "n6", "label": v["code_generator"], "type": "milestone"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "stream into", "edge_type": "depends_on", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "tokens to", "edge_type": "depends_on", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "AST to", "edge_type": "depends_on", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "IR to", "edge_type": "depends_on", "directed": True},
                        {"id": "e5", "source": "n5", "target": "n6", "label": "optimized IR to", "edge_type": "depends_on", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"lexer": "Lexical Token Scanner", "parser": "LALR(1) Syntax Parser", "semantic_analyzer": "Type Checker & Symbol Table", "optimizer": "LLVM SSA Optimizer Passes", "code_generator": "x86-64 Machine Code Emitter"},
                {"lexer": "Regular Expression Lexer", "parser": "Recursive Descent Parser", "semantic_analyzer": "Scope & Type Validator", "optimizer": "Dead Code Elimination Pass", "code_generator": "ARM64 Assembly Generator"}
            ]
        },
        {
            "template_id": "dep_database_migration_deploy",
            "domain": "infrastructure_operations",
            "complexity": "simple",
            "generators": [
                lambda v: {
                    "text": f"Production release dependencies: {v['backup_step']} must complete before running {v['schema_migration']}. Successful schema migration unblocks {v['service_deploy']}. Once services are healthy, {v['smoke_tests']} run. Verification enables updating the {v['dns_switch']}.",
                    "nodes": [
                        {"id": "n1", "label": v["backup_step"], "type": "task"},
                        {"id": "n2", "label": v["schema_migration"], "type": "task"},
                        {"id": "n3", "label": v["service_deploy"], "type": "task"},
                        {"id": "n4", "label": v["smoke_tests"], "type": "task"},
                        {"id": "n5", "label": v["dns_switch"], "type": "milestone"}
                    ],
                    "edges": [
                        {"id": "e1", "source": "n1", "target": "n2", "label": "prerequisite for", "edge_type": "depends_on", "directed": True},
                        {"id": "e2", "source": "n2", "target": "n3", "label": "unblocks", "edge_type": "depends_on", "directed": True},
                        {"id": "e3", "source": "n3", "target": "n4", "label": "triggers", "edge_type": "depends_on", "directed": True},
                        {"id": "e4", "source": "n4", "target": "n5", "label": "approves", "edge_type": "depends_on", "directed": True}
                    ]
                }
            ],
            "param_sets": [
                {"backup_step": "RDS Snapshot Database Backup", "schema_migration": "Alembic Schema Migration", "service_deploy": "Blue/Green Container Rolling Update", "smoke_tests": "Post-Deploy Smoke Test Suite", "dns_switch": "Route53 Production Traffic Flip"},
                {"backup_step": "Full Database Dump", "schema_migration": "Liquibase SQL Execution", "service_deploy": "Kubernetes Pod Deployment", "smoke_tests": "Synthetics Health Check", "dns_switch": "Load Balancer Weight Adjustment"}
            ]
        }
    ]


def generate_full_dataset(seed: int = 42, target_samples_per_family: int = 100) -> List[Dict[str, Any]]:
    random.seed(seed)
    
    family_registry = {
        "flowchart": get_flowchart_templates(),
        "architecture": get_architecture_templates(),
        "concept_map": get_concept_map_templates(),
        "er_diagram": get_er_diagram_templates(),
        "sequence_diagram": get_sequence_diagram_templates(),
        "network_topology": get_network_topology_templates(),
        "dependency_graph": get_dependency_graph_templates()
    }
    
    dataset: List[Dict[str, Any]] = []
    global_counter = 1
    
    prefix_map = {
        "flowchart": "FLOW",
        "architecture": "ARCH",
        "concept_map": "CONC",
        "er_diagram": "ERD",
        "sequence_diagram": "SEQ",
        "network_topology": "NET",
        "dependency_graph": "DEP"
    }

    phrasing_prefixes = [
        "",
        "Please generate a diagram for the following: ",
        "Create a system diagram showing: ",
        "Diagram description: ",
        "Visual model required: ",
        "Construct a detailed diagram: "
    ]
    
    for diagram_type, templates in family_registry.items():
        family_samples = []
        samples_needed = target_samples_per_family
        
        while len(family_samples) < samples_needed:
            for template in templates:
                template_id = template["template_id"]
                domain = template["domain"]
                complexity = template["complexity"]
                
                for param_set in template["param_sets"]:
                    for gen_func in template["generators"]:
                        sample_data = gen_func(param_set)
                        
                        prefix = random.choice(phrasing_prefixes)
                        raw_text = sample_data["text"]
                        final_text = f"{prefix}{raw_text}".strip()
                        
                        sample_id = f"{prefix_map[diagram_type]}_{global_counter:04d}"
                        global_counter += 1
                        
                        entry = {
                            "id": sample_id,
                            "text": final_text,
                            "diagram_type": diagram_type,
                            "nodes": sample_data["nodes"],
                            "edges": sample_data["edges"],
                            "metadata": {
                                "domain": domain,
                                "template_id": template_id,
                                "complexity": complexity,
                                "provenance": "synthetic_controlled_template"
                            }
                        }
                        family_samples.append(entry)
                        if len(family_samples) >= samples_needed:
                            break
                    if len(family_samples) >= samples_needed:
                        break
                if len(family_samples) >= samples_needed:
                    break
        dataset.extend(family_samples)
        
    return dataset


def create_template_isolated_splits(dataset: List[Dict[str, Any]], seed: int = 42) -> Dict[str, List[Dict[str, Any]]]:
    """
    Partitions dataset by template_id to guarantee zero data leakage between
    training (approx 70%), validation (approx 15%), and testing (approx 15%) splits.
    """
    random.seed(seed)
    
    # Group samples by diagram_type and template_id
    grouped_by_type: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for item in dataset:
        dtype = item["diagram_type"]
        tid = item["metadata"]["template_id"]
        if dtype not in grouped_by_type:
            grouped_by_type[dtype] = {}
        if tid not in grouped_by_type[dtype]:
            grouped_by_type[dtype][tid] = []
        grouped_by_type[dtype][tid].append(item)
        
    train_split: List[Dict[str, Any]] = []
    val_split: List[Dict[str, Any]] = []
    test_split: List[Dict[str, Any]] = []
    
    for dtype, templates in grouped_by_type.items():
        template_ids = sorted(list(templates.keys()))
        random.shuffle(template_ids)
        
        n_templates = len(template_ids)
        # Allocate: exactly 1 template to test, 1 template to val, and the remaining (3 or 4) to train
        # For 5 templates: 3 train (60%), 1 val (20%), 1 test (20%)
        # For 6 templates: 4 train (67%), 1 val (16.7%), 1 test (16.7%)
        test_tids = {template_ids[0]}
        val_tids = {template_ids[1]}
        train_tids = set(template_ids[2:])
        
        for tid in train_tids:
            train_split.extend(templates[tid])
        for tid in val_tids:
            val_split.extend(templates[tid])
        for tid in test_tids:
            test_split.extend(templates[tid])
                
    random.shuffle(train_split)
    random.shuffle(val_split)
    random.shuffle(test_split)
    
    return {
        "train": train_split,
        "val": val_split,
        "test": test_split
    }


def main():
    parser = argparse.ArgumentParser(description="Generate AI Diagram Multi-Family Dataset.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument("--samples-per-family", type=int, default=100, help="Target samples per diagram family.")
    parser.add_argument("--output", type=str, default="data/dataset.json", help="Path to main dataset JSON.")
    parser.add_argument("--splits-dir", type=str, default="data/splits", help="Directory for split JSON files.")
    args = parser.parse_args()

    print(f"[*] Generating dataset with seed={args.seed}, {args.samples_per_family} samples/family...")
    dataset = generate_full_dataset(seed=args.seed, target_samples_per_family=args.samples_per_family)
    print(f"[+] Total samples generated: {len(dataset)}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"[+] Main dataset saved to {output_path}")

    splits = create_template_isolated_splits(dataset, seed=args.seed)
    splits_dir = Path(args.splits_dir)
    splits_dir.mkdir(parents=True, exist_ok=True)

    for split_name, split_data in splits.items():
        split_path = splits_dir / f"{split_name}.json"
        with open(split_path, "w", encoding="utf-8") as f:
            json.dump(split_data, f, indent=2)
        print(f"[+] Split '{split_name}' saved to {split_path} ({len(split_data)} samples, {len(split_data)/len(dataset)*100:.1f}%)")


if __name__ == "__main__":
    main()
