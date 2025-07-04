# FHIR MCP Server

A comprehensive Model Context Protocol (MCP) server that provides FHIR (Fast Healthcare Interoperability Resources) functionality with advanced data quality assessment and error handling capabilities.

## 🎯 Overview

This MCP server bridges the gap between AI applications and FHIR healthcare data systems, providing robust tools for accessing patient information, clinical data, and assessing data quality across different FHIR servers. Perfect for healthcare AI development, clinical research, and testing FHIR implementations.

## ✨ Key Features

### 🏥 Comprehensive FHIR Resource Access
- **Patient Management**: Search, retrieve, and analyze patient demographics
- **Clinical Data**: Access observations, conditions, medications, diagnostic reports
- **Care Coordination**: Retrieve care plans and treatment information
- **Server Capabilities**: Query FHIR server metadata and supported features

### 🔍 Advanced Data Quality Assessment
- **Quality Scoring**: 0-100 data quality scores for FHIR servers
- **Integrity Checks**: Detect orphaned references and disconnected data
- **Validation**: Comprehensive FHIR response validation
- **Issue Detection**: Identify data consistency problems automatically

### 🛡️ Enhanced Error Handling
- **HTTP Status Handling**: Proper 404, 401, 403, timeout responses
- **FHIR OperationOutcome**: Standards-compliant error reporting
- **Detailed Logging**: Request/response debugging information
- **Graceful Degradation**: Continues operation despite server issues

### 🧰 Developer-Friendly Tools
- **Async Architecture**: High-performance async/await implementation
- **Pagination Support**: Handle large datasets efficiently
- **Flexible Configuration**: Environment-based server configuration
- **MCP Integration**: Seamless Claude Desktop integration

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or newer
- Claude Desktop (for MCP integration)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jcafazzo/fhir-mcp.git
   cd fhir-mcp
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Claude Desktop**
   
   Add to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "fhir-server": {
         "command": "python3",
         "args": ["/path/to/fhir-mcp/fhir_mcp_server.py"],
         "env": {
           "FHIR_BASE_URL": "https://r4.smarthealthit.org"
         }
       }
     }
   }
   ```

4. **Restart Claude Desktop**

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FHIR_BASE_URL` | FHIR server endpoint | `https://hapi.fhir.org/baseR4` |
| `FHIR_AUTH_TOKEN` | Bearer token for authentication | None |

### Recommended FHIR Servers

| Server | URL | Quality | Use Case |
|--------|-----|---------|----------|
| **SMART Health IT** | `https://r4.smarthealthit.org` | ⭐⭐⭐⭐⭐ | Production testing |
| **Firely Server** | `https://server.fire.ly` | ⭐⭐⭐⭐ | Development |
| **HAPI Test** | `https://hapi.fhir.org/baseR4` | ⭐⭐ | Basic testing |

## 🛠️ Available Tools

### Core Patient Tools
- **`get_patient`** - Retrieve specific patient by ID
- **`search_patients`** - Search patients by name/family
- **`search_all_patients`** - Get all patients (paginated)

### Clinical Data Tools
- **`search_observations`** - Find lab results, vital signs, measurements
- **`search_conditions`** - Access diagnoses and medical conditions
- **`search_medication_requests`** - Retrieve prescriptions and medications
- **`search_diagnostic_reports`** - Get lab reports and diagnostic studies
- **`search_care_plans`** - Access treatment and care plans

### Quality & Diagnostics
- **`assess_data_quality`** - Comprehensive server quality assessment
- **`find_patients_with_conditions`** - Identify patients with clinical data
- **`get_capability_statement`** - Query server capabilities

## 📊 Usage Examples

### Basic Patient Search
```
"Search for patients named 'Smith' and show their demographics"
```

### Diabetes Management Workflow
```
"Find all patients with diabetes conditions, then show their:
- Current medications
- Recent glucose observations  
- Active care plans
- Latest diagnostic reports"
```

### Data Quality Assessment
```
"Assess the data quality of this FHIR server and identify any issues"
```

### Research Query
```
"Find patients with conditions containing 'diabetes' and analyze their 
medication patterns over time"
```

## 🏥 Healthcare Use Cases

### Clinical Research
- **Population Studies**: Analyze patient cohorts across multiple conditions
- **Treatment Outcomes**: Track medication effectiveness and care plan adherence
- **Data Quality**: Validate FHIR implementations before production use

### AI Development
- **Training Data**: Access clean, validated healthcare datasets
- **Model Testing**: Evaluate AI models against real clinical scenarios
- **Integration Testing**: Verify FHIR API compatibility

### Quality Assurance
- **Server Validation**: Assess FHIR server implementations
- **Data Integrity**: Identify orphaned records and missing references
- **Compliance Testing**: Verify standards adherence

## 🔒 Security & Privacy

- **No PHI Storage**: Server operates read-only, no data retention
- **Configurable Auth**: Support for Bearer token authentication
- **Audit Logging**: Comprehensive request/response logging
- **Error Handling**: Secure error responses without data leakage

## 🧪 Testing

### Test Server Quality
```python
# Test different FHIR servers
python3 fhir_mcp_server.py
```

Use the `assess_data_quality` tool to evaluate:
- Data completeness (0-100 score)
- Reference integrity
- Resource availability
- Error rates

### Synthetic Data Testing
Works excellently with:
- **Synthea**: Realistic synthetic patient data
- **MIMIC-IV FHIR**: Real anonymized hospital data
- **Custom datasets**: Load your own test data

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone and setup development environment
git clone https://github.com/jcafazzo/fhir-mcp.git
cd fhir-mcp
pip install -r requirements.txt
python3 fhir_mcp_server.py  # Test locally
```

### Roadmap
- [ ] Bulk FHIR operations support
- [ ] Temporal data analysis tools
- [ ] Enhanced MIMIC-IV integration
- [ ] Performance optimization
- [ ] Additional FHIR resource types

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Claude Code integration guide
- **[FHIR R4 Specification](https://hl7.org/fhir/R4/)** - Official FHIR documentation
- **[MCP Protocol](https://modelcontextprotocol.io/)** - Model Context Protocol specification

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **HL7 FHIR Community** for the FHIR specification
- **Anthropic** for the Model Context Protocol
- **SMART Health IT** for excellent test servers
- **Synthea Project** for realistic synthetic data

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/jcafazzo/fhir-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jcafazzo/fhir-mcp/discussions)
- **Documentation**: Check [CLAUDE.md](CLAUDE.md) for detailed setup

---

**Built with ❤️ for the healthcare AI community**