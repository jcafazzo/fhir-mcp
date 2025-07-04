#!/usr/bin/env python3
"""
Working FHIR MCP Server - Back to the version that worked
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urljoin, urlparse

print("Working FHIR MCP Server starting...", file=sys.stderr)

try:
    import httpx
    print("httpx imported successfully", file=sys.stderr)
except ImportError as e:
    print(f"Failed to import httpx: {e}", file=sys.stderr)
    sys.exit(1)

try:
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        ListToolsResult,
        TextContent,
        Tool,
    )
    from mcp.server import NotificationOptions, Server
    print("MCP imports successful", file=sys.stderr)
except ImportError as e:
    print(f"Failed to import MCP: {e}", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FHIRClient:
    """Client for interacting with FHIR endpoints"""
    
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.client = httpx.AsyncClient(timeout=30.0)
        print(f"FHIR Client initialized with base_url: {self.base_url}", file=sys.stderr)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for FHIR requests"""
        headers = {
            'Accept': 'application/fhir+json',
            'Content-Type': 'application/fhir+json'
        }
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        return headers
        
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to FHIR endpoint with enhanced error handling"""
        url = urljoin(self.base_url + '/', endpoint)
        headers = self._get_headers()
        
        try:
            print(f"Making FHIR request: {method} {url}", file=sys.stderr)
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            
            # Enhanced status code handling
            if response.status_code == 404:
                return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "not-found", "details": {"text": f"Resource not found: {endpoint}"}}]}
            elif response.status_code == 401:
                return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "security", "details": {"text": "Authentication required"}}]}
            elif response.status_code == 403:
                return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "forbidden", "details": {"text": "Access forbidden"}}]}
            
            response.raise_for_status()
            
            # Validate response is JSON
            try:
                result = response.json()
                print(f"FHIR response received: {result.get('resourceType', 'Unknown')} with {len(str(result))} chars", file=sys.stderr)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "invalid", "details": {"text": f"Invalid JSON response: {str(e)}"}}]}
                
        except httpx.TimeoutException:
            logger.error(f"FHIR request timeout for {url}")
            return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "timeout", "details": {"text": "Request timed out"}}]}
        except httpx.HTTPError as e:
            logger.error(f"FHIR request failed: {e}")
            return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception", "details": {"text": f"HTTP error: {str(e)}"}}]}
        except Exception as e:
            logger.error(f"Request processing failed: {e}")
            return {"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "exception", "details": {"text": f"Unexpected error: {str(e)}"}}]}
            
    async def get_patient(self, patient_id: str) -> Dict[str, Any]:
        """Get a specific patient by ID"""
        return await self._make_request('GET', f'Patient/{patient_id}')
        
    async def search_patients(self, **params) -> Dict[str, Any]:
        """Search for patients with given parameters"""
        return await self._make_request('GET', 'Patient', params=params)
        
    async def search_observations(self, **params) -> Dict[str, Any]:
        """Search for observations with given parameters"""
        return await self._make_request('GET', 'Observation', params=params)
        
    async def get_capability_statement(self) -> Dict[str, Any]:
        """Get FHIR server capability statement"""
        return await self._make_request('GET', 'metadata')
    
    async def search_conditions(self, **params) -> Dict[str, Any]:
        """Search for conditions (diagnoses) with given parameters"""
        return await self._make_request('GET', 'Condition', params=params)
    
    async def search_medication_requests(self, **params) -> Dict[str, Any]:
        """Search for medication requests with given parameters"""
        return await self._make_request('GET', 'MedicationRequest', params=params)
    
    async def search_diagnostic_reports(self, **params) -> Dict[str, Any]:
        """Search for diagnostic reports with given parameters"""
        return await self._make_request('GET', 'DiagnosticReport', params=params)
    
    async def search_care_plans(self, **params) -> Dict[str, Any]:
        """Search for care plans with given parameters"""
        return await self._make_request('GET', 'CarePlan', params=params)
    
    def _validate_fhir_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and analyze FHIR response quality"""
        validation_result = {
            "is_valid": True,
            "issues": [],
            "data_quality": {},
            "resource_type": response.get('resourceType', 'Unknown')
        }
        
        # Check if it's an OperationOutcome (error response)
        if response.get('resourceType') == 'OperationOutcome':
            validation_result["is_valid"] = False
            issues = response.get('issue', [])
            for issue in issues:
                validation_result["issues"].append({
                    "severity": issue.get('severity', 'unknown'),
                    "code": issue.get('code', 'unknown'),
                    "details": issue.get('details', {}).get('text', 'No details')
                })
            return validation_result
        
        # Check for Bundle (search results)
        if response.get('resourceType') == 'Bundle':
            entries = response.get('entry', [])
            total = response.get('total', 0)
            
            validation_result["data_quality"] = {
                "total_resources": total,
                "returned_resources": len(entries),
                "has_next_page": any(link.get('relation') == 'next' for link in response.get('link', [])),
                "resource_types": list(set(entry.get('resource', {}).get('resourceType') for entry in entries if 'resource' in entry))
            }
            
            # Check for orphaned references
            patient_refs = set()
            actual_patients = set()
            
            for entry in entries:
                resource = entry.get('resource', {})
                resource_type = resource.get('resourceType')
                
                if resource_type == 'Patient':
                    actual_patients.add(resource.get('id'))
                elif 'subject' in resource and 'reference' in resource['subject']:
                    ref = resource['subject']['reference']
                    if '/' in ref:
                        patient_refs.add(ref.split('/')[-1])
            
            if patient_refs and actual_patients:
                orphaned = patient_refs - actual_patients
                if orphaned:
                    validation_result["issues"].append({
                        "severity": "warning",
                        "code": "orphaned-references",
                        "details": f"Found {len(orphaned)} orphaned patient references"
                    })
                    validation_result["data_quality"]["orphaned_patient_refs"] = len(orphaned)
        
        return validation_result
    
    async def assess_data_quality(self, resource_type: str = None) -> Dict[str, Any]:
        """Assess overall data quality of the FHIR server"""
        assessment = {
            "server_url": self.base_url,
            "timestamp": datetime.now().isoformat(),
            "resource_assessments": {}
        }
        
        # Test basic resources
        test_resources = ['Patient', 'Observation', 'Condition', 'MedicationRequest'] if not resource_type else [resource_type]
        
        for resource in test_resources:
            try:
                # Small sample search
                result = await self._make_request('GET', resource, params={'_count': 10})
                validation = self._validate_fhir_response(result)
                
                assessment["resource_assessments"][resource] = {
                    "accessible": validation["is_valid"],
                    "total_available": validation.get("data_quality", {}).get("total_resources", 0),
                    "issues": validation["issues"],
                    "data_quality_score": self._calculate_quality_score(validation)
                }
            except Exception as e:
                assessment["resource_assessments"][resource] = {
                    "accessible": False,
                    "error": str(e),
                    "data_quality_score": 0
                }
        
        return assessment
    
    def _calculate_quality_score(self, validation: Dict[str, Any]) -> float:
        """Calculate a data quality score from 0-100"""
        if not validation["is_valid"]:
            return 0.0
        
        score = 100.0
        
        # Deduct points for issues
        for issue in validation["issues"]:
            if issue["severity"] == "error":
                score -= 30
            elif issue["severity"] == "warning":
                score -= 10
        
        # Check data completeness
        quality = validation.get("data_quality", {})
        if quality.get("orphaned_patient_refs", 0) > 0:
            score -= 20
        
        if quality.get("total_resources", 0) == 0:
            score -= 50
        
        return max(0.0, score)

# Initialize MCP server
server = Server("fhir-mcp-server")
fhir_client: Optional[FHIRClient] = None

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available FHIR tools"""
    print("list_tools handler called", file=sys.stderr)
    
    tools = [
        Tool(
            name="get_patient",
            description="Get a specific patient by their ID",
            inputSchema={
                "type": "object",
                "required": ["patient_id"],
                "properties": {
                    "patient_id": {"type": "string", "description": "The patient ID to retrieve"}
                }
            }
        ),
        Tool(
            name="search_patients",
            description="Search for patients in the FHIR server",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Patient name"},
                    "family": {"type": "string", "description": "Patient family name"},
                    "_count": {"type": "integer", "description": "Number of results", "default": 10}
                }
            }
        ),
        Tool(
            name="search_all_patients",
            description="Get all patients (no filters)",
            inputSchema={
                "type": "object",
                "properties": {
                    "_count": {"type": "integer", "description": "Number of results", "default": 10}
                }
            }
        ),
        Tool(
            name="search_observations",
            description="Search for observations",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient": {"type": "string", "description": "Patient ID"},
                    "_count": {"type": "integer", "description": "Number of results", "default": 10}
                }
            }
        ),
        Tool(
            name="get_capability_statement",
            description="Get FHIR server capabilities",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="search_conditions",
            description="Search for conditions/diagnoses (e.g., diabetes)",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient": {"type": "string", "description": "Patient ID"},
                    "code": {"type": "string", "description": "Condition code (e.g., SNOMED code)"},
                    "clinical-status": {"type": "string", "description": "Clinical status (active, resolved, etc.)"},
                    "_count": {"type": "integer", "description": "Number of results", "default": 10}
                }
            }
        ),
        Tool(
            name="search_medication_requests",
            description="Search for medication requests/prescriptions (e.g., diabetes medications)",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient": {"type": "string", "description": "Patient ID"},
                    "status": {"type": "string", "description": "Status (active, completed, etc.)"},
                    "intent": {"type": "string", "description": "Intent (order, plan, etc.)"},
                    "_count": {"type": "integer", "description": "Number of results", "default": 10}
                }
            }
        ),
        Tool(
            name="search_diagnostic_reports",
            description="Search for diagnostic reports (e.g., lab results, HbA1c tests)",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient": {"type": "string", "description": "Patient ID"},
                    "status": {"type": "string", "description": "Report status"},
                    "category": {"type": "string", "description": "Category of report"},
                    "_count": {"type": "integer", "description": "Number of results", "default": 10}
                }
            }
        ),
        Tool(
            name="search_care_plans",
            description="Search for care plans (e.g., diabetes management plans)",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient": {"type": "string", "description": "Patient ID"},
                    "status": {"type": "string", "description": "Plan status (active, completed, etc.)"},
                    "category": {"type": "string", "description": "Category of care plan"},
                    "_count": {"type": "integer", "description": "Number of results", "default": 10}
                }
            }
        ),
        Tool(
            name="find_patients_with_conditions",
            description="Find unique patient IDs from condition records (useful when patient records are missing)",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Condition code to filter by (optional)"},
                    "_count": {"type": "integer", "description": "Number of results", "default": 100}
                }
            }
        ),
        Tool(
            name="assess_data_quality",
            description="Assess the data quality and integrity of the FHIR server",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_type": {"type": "string", "description": "Specific resource type to assess (optional, defaults to all basic types)"}
                }
            }
        )
    ]
    
    print(f"Returning {len(tools)} tools", file=sys.stderr)
    return tools

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls"""
    print(f"call_tool handler called with: {name}", file=sys.stderr)
    print(f"Arguments: {arguments}", file=sys.stderr)
    
    if not fhir_client:
        return [TextContent(type="text", text="FHIR client not initialized")]
        
    try:
        if name == "get_patient":
            patient_id = arguments.get('patient_id')
            if not patient_id:
                return [TextContent(type="text", text="Patient ID is required")]
            
            try:
                result = await fhir_client.get_patient(patient_id)
                
                # Extract patient details
                patient_id = result.get('id', 'Unknown')
                name = "Unknown Name"
                
                if 'name' in result and result['name']:
                    name_obj = result['name'][0]
                    family = name_obj.get('family', '')
                    given = ' '.join(name_obj.get('given', []))
                    name = f"{given} {family}".strip()
                
                birth_date = result.get('birthDate', 'Unknown')
                gender = result.get('gender', 'Unknown')
                
                response_lines = [f"Patient found:"]
                response_lines.append(f"ID: {patient_id}")
                response_lines.append(f"Name: {name}")
                response_lines.append(f"Date of Birth: {birth_date}")
                response_lines.append(f"Gender: {gender}")
                
                # Add additional details if available
                if 'address' in result and result['address']:
                    address = result['address'][0]
                    city = address.get('city', '')
                    state = address.get('state', '')
                    country = address.get('country', '')
                    response_lines.append(f"Location: {city}, {state} {country}".strip())
                
                if 'telecom' in result:
                    for contact in result['telecom']:
                        if contact.get('system') == 'phone':
                            response_lines.append(f"Phone: {contact.get('value', 'Unknown')}")
                        elif contact.get('system') == 'email':
                            response_lines.append(f"Email: {contact.get('value', 'Unknown')}")
                
                return [TextContent(type="text", text="\n".join(response_lines))]
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return [TextContent(type="text", text=f"Patient with ID {patient_id} not found")]
                else:
                    return [TextContent(type="text", text=f"Error retrieving patient: {str(e)}")]
            
        elif name == "search_patients":
            result = await fhir_client.search_patients(**arguments)
            total = result.get('total', 0)
            entries = result.get('entry', [])
            
            response_lines = [f"Search completed. Found {total} patients in total."]
            response_lines.append(f"Returned {len(entries)} entries in this page.")
            
            if entries:
                response_lines.append("\nPatients found:")
                for entry in entries[:10]:  # Show first 10
                    resource = entry.get('resource', {})
                    patient_id = resource.get('id', 'Unknown')
                    name = "Unknown Name"
                    
                    if 'name' in resource and resource['name']:
                        name_obj = resource['name'][0]
                        family = name_obj.get('family', '')
                        given = ' '.join(name_obj.get('given', []))
                        name = f"{given} {family}".strip()
                    
                    birth_date = resource.get('birthDate', 'Unknown')
                    gender = resource.get('gender', 'Unknown')
                    
                    response_lines.append(f"- ID: {patient_id} | Name: {name} | DOB: {birth_date} | Gender: {gender}")
            else:
                response_lines.append("No entries found in response")
                
            return [TextContent(type="text", text="\n".join(response_lines))]
            
        elif name == "search_all_patients":
            # Search with no filters
            result = await fhir_client.search_patients(_count=arguments.get('_count', 10))
            total = result.get('total', 0)
            entries = result.get('entry', [])
            
            response_lines = [f"Total patients in system: {total}"]
            response_lines.append(f"Returned in this page: {len(entries)}")
            
            if entries:
                response_lines.append("\nPatients found:")
                for entry in entries[:10]:
                    resource = entry.get('resource', {})
                    patient_id = resource.get('id', 'Unknown')
                    name = "Unknown Name"
                    
                    if 'name' in resource and resource['name']:
                        name_obj = resource['name'][0]
                        family = name_obj.get('family', '')
                        given = ' '.join(name_obj.get('given', []))
                        name = f"{given} {family}".strip()
                    
                    birth_date = resource.get('birthDate', 'Unknown')
                    gender = resource.get('gender', 'Unknown')
                    
                    response_lines.append(f"- ID: {patient_id} | Name: {name} | DOB: {birth_date} | Gender: {gender}")
            else:
                response_lines.append("No entries found - this indicates an issue with the search")
                
            return [TextContent(type="text", text="\n".join(response_lines))]
            
        elif name == "search_observations":
            result = await fhir_client.search_observations(**arguments)
            total = result.get('total', 0)
            entries = result.get('entry', [])
            
            response_lines = [f"Found {total} observations total"]
            response_lines.append(f"Returned {len(entries)} entries in this page")
            
            if entries:
                response_lines.append("\nObservations:")
                for entry in entries[:5]:  # Show first 5
                    resource = entry.get('resource', {})
                    obs_id = resource.get('id', 'Unknown')
                    
                    # Get basic info
                    code = resource.get('code', {}).get('text', 'Unknown observation')
                    value = resource.get('valueString', resource.get('valueQuantity', {}).get('value', 'No value'))
                    
                    response_lines.append(f"- ID: {obs_id} | {code} | Value: {value}")
            else:
                response_lines.append("No observation entries found")
                
            return [TextContent(type="text", text="\n".join(response_lines))]
            
        elif name == "get_capability_statement":
            result = await fhir_client.get_capability_statement()
            fhir_version = result.get('fhirVersion', 'Unknown')
            publisher = result.get('publisher', 'Unknown')
            
            response_lines = [f"FHIR Version: {fhir_version}"]
            response_lines.append(f"Publisher: {publisher}")
            
            if 'rest' in result:
                response_lines.append(f"REST endpoints: {len(result['rest'])}")
                for rest in result['rest']:
                    if 'resource' in rest:
                        response_lines.append(f"Supported resources: {len(rest['resource'])}")
                        break
            
            return [TextContent(type="text", text="\n".join(response_lines))]
            
        elif name == "search_conditions":
            result = await fhir_client.search_conditions(**arguments)
            total = result.get('total', 0)
            entries = result.get('entry', [])
            
            response_lines = [f"Found {total} conditions total"]
            response_lines.append(f"Returned {len(entries)} entries in this page")
            
            if entries:
                response_lines.append("\nConditions:")
                for entry in entries[:10]:
                    resource = entry.get('resource', {})
                    condition_id = resource.get('id', 'Unknown')
                    
                    # Get condition details
                    code_text = 'Unknown condition'
                    if 'code' in resource and 'text' in resource['code']:
                        code_text = resource['code']['text']
                    elif 'code' in resource and 'coding' in resource['code'] and resource['code']['coding']:
                        code_text = resource['code']['coding'][0].get('display', 'Unknown')
                    
                    clinical_status = 'Unknown'
                    if 'clinicalStatus' in resource and 'coding' in resource['clinicalStatus']:
                        clinical_status = resource['clinicalStatus']['coding'][0].get('code', 'Unknown')
                    
                    onset = resource.get('onsetDateTime', 'Unknown onset')
                    
                    # Get patient reference
                    patient_ref = 'Unknown patient'
                    if 'subject' in resource and 'reference' in resource['subject']:
                        patient_ref = resource['subject']['reference']
                        # Extract just the ID from references like "Patient/625760"
                        if '/' in patient_ref:
                            patient_ref = patient_ref.split('/')[-1]
                    
                    response_lines.append(f"- ID: {condition_id} | Patient: {patient_ref} | {code_text} | Status: {clinical_status} | Onset: {onset}")
            else:
                response_lines.append("No conditions found")
                
            return [TextContent(type="text", text="\n".join(response_lines))]
            
        elif name == "search_medication_requests":
            result = await fhir_client.search_medication_requests(**arguments)
            total = result.get('total', 0)
            entries = result.get('entry', [])
            
            response_lines = [f"Found {total} medication requests total"]
            response_lines.append(f"Returned {len(entries)} entries in this page")
            
            if entries:
                response_lines.append("\nMedication Requests:")
                for entry in entries[:10]:
                    resource = entry.get('resource', {})
                    request_id = resource.get('id', 'Unknown')
                    
                    # Get medication details
                    med_text = 'Unknown medication'
                    if 'medicationCodeableConcept' in resource:
                        if 'text' in resource['medicationCodeableConcept']:
                            med_text = resource['medicationCodeableConcept']['text']
                        elif 'coding' in resource['medicationCodeableConcept'] and resource['medicationCodeableConcept']['coding']:
                            med_text = resource['medicationCodeableConcept']['coding'][0].get('display', 'Unknown')
                    
                    status = resource.get('status', 'Unknown')
                    intent = resource.get('intent', 'Unknown')
                    authored_on = resource.get('authoredOn', 'Unknown date')
                    
                    response_lines.append(f"- ID: {request_id} | {med_text} | Status: {status} | Intent: {intent} | Date: {authored_on}")
            else:
                response_lines.append("No medication requests found")
                
            return [TextContent(type="text", text="\n".join(response_lines))]
            
        elif name == "search_diagnostic_reports":
            result = await fhir_client.search_diagnostic_reports(**arguments)
            total = result.get('total', 0)
            entries = result.get('entry', [])
            
            response_lines = [f"Found {total} diagnostic reports total"]
            response_lines.append(f"Returned {len(entries)} entries in this page")
            
            if entries:
                response_lines.append("\nDiagnostic Reports:")
                for entry in entries[:10]:
                    resource = entry.get('resource', {})
                    report_id = resource.get('id', 'Unknown')
                    
                    # Get report details
                    code_text = 'Unknown report'
                    if 'code' in resource and 'text' in resource['code']:
                        code_text = resource['code']['text']
                    elif 'code' in resource and 'coding' in resource['code'] and resource['code']['coding']:
                        code_text = resource['code']['coding'][0].get('display', 'Unknown')
                    
                    status = resource.get('status', 'Unknown')
                    effective_date = resource.get('effectiveDateTime', 'Unknown date')
                    
                    # Get category if available
                    category = 'Unknown category'
                    if 'category' in resource and resource['category'] and 'coding' in resource['category'][0]:
                        category = resource['category'][0]['coding'][0].get('display', 'Unknown')
                    
                    response_lines.append(f"- ID: {report_id} | {code_text} | Category: {category} | Status: {status} | Date: {effective_date}")
            else:
                response_lines.append("No diagnostic reports found")
                
            return [TextContent(type="text", text="\n".join(response_lines))]
            
        elif name == "search_care_plans":
            result = await fhir_client.search_care_plans(**arguments)
            total = result.get('total', 0)
            entries = result.get('entry', [])
            
            response_lines = [f"Found {total} care plans total"]
            response_lines.append(f"Returned {len(entries)} entries in this page")
            
            if entries:
                response_lines.append("\nCare Plans:")
                for entry in entries[:10]:
                    resource = entry.get('resource', {})
                    plan_id = resource.get('id', 'Unknown')
                    
                    # Get plan details
                    title = resource.get('title', 'Untitled plan')
                    status = resource.get('status', 'Unknown')
                    intent = resource.get('intent', 'Unknown')
                    created = resource.get('created', 'Unknown date')
                    
                    # Get category if available
                    category = 'Unknown category'
                    if 'category' in resource and resource['category'] and 'text' in resource['category'][0]:
                        category = resource['category'][0]['text']
                    elif 'category' in resource and resource['category'] and 'coding' in resource['category'][0]:
                        category = resource['category'][0]['coding'][0].get('display', 'Unknown')
                    
                    response_lines.append(f"- ID: {plan_id} | {title} | Category: {category} | Status: {status} | Intent: {intent} | Created: {created}")
            else:
                response_lines.append("No care plans found")
                
            return [TextContent(type="text", text="\n".join(response_lines))]
            
        elif name == "find_patients_with_conditions":
            result = await fhir_client.search_conditions(**arguments)
            entries = result.get('entry', [])
            
            # Extract unique patient IDs
            patient_ids = set()
            for entry in entries:
                resource = entry.get('resource', {})
                if 'subject' in resource and 'reference' in resource['subject']:
                    patient_ref = resource['subject']['reference']
                    if '/' in patient_ref:
                        patient_id = patient_ref.split('/')[-1]
                        patient_ids.add(patient_id)
            
            response_lines = [f"Found {len(patient_ids)} unique patients with conditions"]
            if patient_ids:
                response_lines.append("\nPatient IDs:")
                for pid in sorted(patient_ids)[:20]:  # Show first 20
                    response_lines.append(f"- {pid}")
                if len(patient_ids) > 20:
                    response_lines.append(f"... and {len(patient_ids) - 20} more")
            else:
                response_lines.append("No patient IDs found in condition records")
                
            return [TextContent(type="text", text="\n".join(response_lines))]
            
        elif name == "assess_data_quality":
            resource_type = arguments.get('resource_type')
            assessment = await fhir_client.assess_data_quality(resource_type)
            
            response_lines = [f"FHIR Server Data Quality Assessment"]
            response_lines.append(f"Server: {assessment['server_url']}")
            response_lines.append(f"Timestamp: {assessment['timestamp']}")
            response_lines.append("")
            
            overall_score = 0
            resource_count = 0
            
            for resource, data in assessment['resource_assessments'].items():
                response_lines.append(f"📊 {resource} Resource:")
                response_lines.append(f"  ✅ Accessible: {data['accessible']}")
                
                if data['accessible']:
                    response_lines.append(f"  📈 Quality Score: {data['data_quality_score']:.1f}/100")
                    response_lines.append(f"  📋 Total Available: {data['total_available']}")
                    
                    if data['issues']:
                        response_lines.append(f"  ⚠️  Issues Found:")
                        for issue in data['issues']:
                            response_lines.append(f"    - {issue['severity'].upper()}: {issue['details']}")
                    else:
                        response_lines.append(f"  ✅ No issues detected")
                    
                    overall_score += data['data_quality_score']
                    resource_count += 1
                else:
                    response_lines.append(f"  ❌ Error: {data.get('error', 'Unknown error')}")
                
                response_lines.append("")
            
            if resource_count > 0:
                avg_score = overall_score / resource_count
                response_lines.append(f"🎯 Overall Data Quality Score: {avg_score:.1f}/100")
                
                if avg_score >= 80:
                    response_lines.append("✅ EXCELLENT: This server has high-quality, well-connected data")
                elif avg_score >= 60:
                    response_lines.append("⚠️  GOOD: This server has decent data with some issues")
                elif avg_score >= 40:
                    response_lines.append("⚠️  FAIR: This server has significant data quality issues")
                else:
                    response_lines.append("❌ POOR: This server has major data quality problems")
            
            return [TextContent(type="text", text="\n".join(response_lines))]
            
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
    except Exception as e:
        error_msg = f"Error calling tool {name}: {str(e)}"
        print(error_msg, file=sys.stderr)
        return [TextContent(type="text", text=error_msg)]

async def main():
    """Main server entry point"""
    global fhir_client
    
    print("Starting main function", file=sys.stderr)
    
    # Get configuration from environment
    fhir_base_url = os.environ.get("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4")
    fhir_auth_token = os.environ.get("FHIR_AUTH_TOKEN")
    
    print(f"FHIR Base URL: {fhir_base_url}", file=sys.stderr)
    
    # Initialize FHIR client
    try:
        fhir_client = FHIRClient(fhir_base_url, fhir_auth_token)
        print(f"FHIR client initialized successfully", file=sys.stderr)
    except Exception as e:
        print(f"Failed to initialize FHIR client: {e}", file=sys.stderr)
        return
    
    # Run server
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, 
                write_stream, 
                InitializationOptions(
                    server_name="fhir-mcp-server",
                    server_version="1.0.0",
                    capabilities={}
                )
            )
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    print("Script starting", file=sys.stderr)
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)