# SOC 2 Trust Service Criteria (TSC) Reference

**Document Purpose**: Comprehensive reference for SOC 2 Trust Service Criteria  
**Last Updated**: October 11, 2025  
**Source**: AICPA Trust Services Criteria (2017/Updated 2025)

---

## Overview

SOC 2 (Service Organization Control 2) is an auditing standard developed by the American Institute of CPAs (AICPA) for service providers storing customer data in the cloud. It ensures that service providers securely manage data to protect the interests and privacy of their clients.

### Key Points

- **Type I**: Examines whether controls are designed appropriately at a specific point in time
- **Type II**: Tests whether controls operate effectively over a period (typically 3-12 months)
- **Mandatory**: Security criterion is always required
- **Optional**: Availability, Processing Integrity, Confidentiality, Privacy can be added based on services

---

## The Five Trust Service Criteria

### 1. SECURITY (Common Criteria - MANDATORY)

**Definition**: Information and systems are protected against unauthorized access, unauthorized disclosure of information, and damage to systems that could compromise the availability, integrity, confidentiality, and privacy of information or systems and affect the entity's ability to achieve its objectives.

#### Key Control Areas

**CC1: Control Environment**
- Demonstrates commitment to integrity and ethical values
- Board independence and oversight
- Management establishes accountability structures
- Competence and skill assessment
- Performance measures, incentives, and rewards aligned with objectives

**CC2: Communication and Information**
- Internal and external communication objectives
- Information system requirements defined
- Quality information provided
- Security objectives communicated to vendors
- System changes communicated to stakeholders

**CC3: Risk Assessment**
- Specifies objectives clearly
- Identifies and analyzes risks
- Assesses fraud risk
- Identifies and assesses changes that could impact controls
- Regular vulnerability assessments

**CC4: Monitoring Activities**
- Ongoing and separate evaluations
- Evaluates and communicates deficiencies
- Third-party monitoring (if applicable)

**CC5: Control Activities**
- Selects and develops control activities
- Selects and develops general IT controls
- Deploys control activities through policies and procedures

**CC6: Logical and Physical Access Controls**
- Authorization and authentication mechanisms
- Role-based access control (RBAC)
- Multi-factor authentication (MFA) where appropriate
- Least privilege principle
- Access reviews and recertification
- Physical security controls for data centers
- Network segmentation and firewalls
- Intrusion detection/prevention systems (IDS/IPS)
- Secure disposal of media and equipment

**CC7: System Operations**
- Change management procedures
- Capacity planning and monitoring
- Incident detection and response
- Backup and recovery procedures
- System availability monitoring
- Patch management
- Vulnerability management

**CC8: Change Management**
- Formal change approval process
- Testing before deployment
- Emergency change procedures
- Version control and code repository
- Rollback capabilities
- Change documentation

**CC9: Risk Mitigation**
- Business continuity planning
- Disaster recovery procedures
- Insurance and risk transfer
- Vendor management and due diligence
- Security event logging and monitoring
- Periodic testing of incident response

---

### 2. AVAILABILITY (Optional)

**Definition**: The system is available for operation and use as committed or agreed upon.

#### Key Requirements

**A1.1 - Availability Commitments**
- Service level agreements (SLAs) defined
- Uptime commitments documented
- Performance baselines established

**A1.2 - System Monitoring**
- Real-time availability monitoring
- Alert mechanisms for downtime
- Performance metrics tracking
- Capacity planning and forecasting

**A1.3 - Incident Management**
- Incident detection and classification
- Incident response procedures
- Escalation procedures
- Root cause analysis
- Communication to stakeholders during incidents

**A1.4 - Business Continuity & Disaster Recovery**
- Business continuity plan (BCP) documented
- Disaster recovery plan (DRP) documented
- Recovery time objectives (RTO) defined
- Recovery point objectives (RPO) defined
- Regular testing of BC/DR plans (at least annually)
- Backup verification and restoration testing
- Geographic redundancy (if applicable)
- Failover procedures

**A1.5 - Infrastructure Management**
- Redundant systems and components
- Load balancing
- Auto-scaling capabilities
- Network infrastructure resilience
- Power and cooling redundancy (data center)

---

### 3. PROCESSING INTEGRITY (Optional)

**Definition**: System processing is complete, valid, accurate, timely, and authorized to meet the entity's objectives.

#### Key Requirements

**PI1.1 - Processing Objectives**
- Processing requirements documented
- Data validation rules defined
- Authorization requirements established
- Error handling procedures

**PI1.2 - Processing Completeness**
- All transactions are processed
- Duplicate transaction prevention
- Lost transaction detection
- Reconciliation procedures

**PI1.3 - Processing Accuracy**
- Input validation controls
- Calculation accuracy
- Data transformation accuracy
- Output validation

**PI1.4 - Processing Validity**
- Authorization controls for processing
- Data source authentication
- Transaction approval workflows
- Audit trails for processing activities

**PI1.5 - Processing Timeliness**
- Processing deadlines defined
- Monitoring of processing times
- Alerts for delayed processing
- Service level monitoring

---

### 4. CONFIDENTIALITY (Optional)

**Definition**: Information designated as confidential is protected as committed or agreed.

#### Key Requirements

**C1.1 - Confidentiality Commitments**
- Data classification scheme
- Confidential data identified and labeled
- Contractual confidentiality obligations
- Non-disclosure agreements (NDAs)

**C1.2 - Access to Confidential Information**
- Need-to-know access controls
- Role-based access for confidential data
- Access logging and monitoring
- Regular access reviews

**C1.3 - Confidential Information Protection**
- Encryption at rest for confidential data
- Encryption in transit (TLS 1.2+)
- Secure key management
- Data masking/tokenization where appropriate

**C1.4 - Confidential Information Disposal**
- Secure deletion procedures
- Media sanitization standards
- Certificate of destruction (where required)
- Retention policy compliance

**C1.5 - Confidential Information Disclosure**
- Disclosure authorization process
- Logging of all disclosures
- Third-party confidentiality agreements
- Vendor security assessments

---

### 5. PRIVACY (Optional)

**Definition**: Personal information is collected, used, retained, disclosed, and disposed of in conformity with the commitments in the entity's privacy notice and with criteria set forth in Generally Accepted Privacy Principles (GAPP).

#### Key Requirements

**P1.0 - Privacy Notice and Communication**
- Privacy policy published and accessible
- Privacy notice provided at collection
- Changes to privacy policy communicated
- Clear and understandable language

**P2.0 - Choice and Consent**
- Explicit consent for data collection
- Opt-in for sensitive data
- Opt-out mechanisms provided
- Consent withdrawal process

**P3.0 - Collection**
- Limited to stated purposes
- Lawful basis for collection
- Minimum necessary data collected
- Special category data safeguards

**P4.0 - Use, Retention, and Disposal**
- Used only for stated purposes
- Retention periods defined
- Secure disposal procedures
- Data minimization principles

**P5.0 - Access**
- Individual access to their data
- Mechanisms to request data copies
- Reasonable timeframes for responses
- Identity verification before access

**P6.0 - Disclosure to Third Parties**
- Disclosure only with consent or legal basis
- Third-party agreements in place
- Notification of disclosures
- Vendor privacy assessments

**P7.0 - Security for Privacy**
- All security controls from CC criteria
- Encryption of personal data
- Data breach notification procedures
- Privacy impact assessments (PIAs)

**P8.0 - Quality**
- Data accuracy procedures
- Mechanisms to correct inaccurate data
- Data validation at collection
- Regular data quality reviews

**P9.0 - Monitoring and Enforcement**
- Privacy compliance monitoring
- Privacy training for staff
- Privacy incident response
- Regulatory compliance tracking (GDPR, CCPA, etc.)

---

## Control Implementation Levels

### Level 1: Policies and Procedures
- Written documentation of controls
- Management approval
- Regular review and updates

### Level 2: Implementation
- Controls deployed in production
- Tools and systems in place
- Staff trained on procedures

### Level 3: Monitoring and Evidence
- Ongoing monitoring mechanisms
- Evidence collection (logs, tickets, reports)
- Regular testing of controls

### Level 4: Continuous Improvement
- Metrics and KPIs tracked
- Regular audits and assessments
- Remediation of identified gaps
- Management review and optimization

---

## Evidence Requirements

For SOC 2 Type II audits, auditors will request evidence including:

### Documentation
- ✅ Policies and procedures
- ✅ System architecture diagrams
- ✅ Network diagrams
- ✅ Data flow diagrams
- ✅ Risk assessments
- ✅ Business continuity/disaster recovery plans
- ✅ Vendor contracts and assessments
- ✅ Training materials and records

### Technical Evidence
- ✅ Access control lists and reviews
- ✅ System logs (authentication, changes, security events)
- ✅ Firewall and network rules
- ✅ Vulnerability scan reports
- ✅ Penetration test reports
- ✅ Backup logs and restoration tests
- ✅ Change management tickets
- ✅ Incident response records
- ✅ Monitoring alerts and responses

### Process Evidence
- ✅ Meeting minutes (security review, risk committee)
- ✅ Employee background check records
- ✅ Training completion records
- ✅ Access request and approval records
- ✅ Termination checklists
- ✅ Vendor review documentation
- ✅ Compliance monitoring reports

### Testing Evidence
- ✅ Control testing results
- ✅ DR drill documentation
- ✅ Incident response tabletop exercises
- ✅ User access testing samples
- ✅ Change management samples

---

## Audit Timeline

### Type I Timeline (Point-in-Time)
- **Week 1-2**: Readiness assessment
- **Week 3-4**: Gap remediation
- **Week 5-6**: Pre-audit preparation
- **Week 7**: Audit fieldwork (1-3 days on-site/virtual)
- **Week 8**: Report delivery

### Type II Timeline (Continuous, typically 6-12 months)
- **Month 1**: Audit planning and scoping
- **Month 2-8**: Observation period (controls operating)
- **Month 9-10**: Evidence collection and control testing
- **Month 11**: Fieldwork and interviews
- **Month 12**: Report drafting and delivery

---

## Common Pitfalls to Avoid

1. ❌ **Inadequate documentation**: Controls must be documented in writing
2. ❌ **Lack of evidence**: Logs, tickets, and records must exist for entire audit period
3. ❌ **Inconsistent implementation**: Controls must operate throughout observation period
4. ❌ **Missing access reviews**: User access must be reviewed at least quarterly
5. ❌ **No vendor assessments**: Third-party vendors must be assessed for security
6. ❌ **Incomplete change management**: All changes must follow formal process
7. ❌ **Inadequate testing**: DR/BC plans must be tested at least annually
8. ❌ **Missing training records**: Security awareness training must be documented
9. ❌ **Weak password policies**: Must meet industry standards (complexity, MFA)
10. ❌ **No incident response plan**: Must be documented and tested

---

## Key Success Factors

### 1. Executive Commitment
- Leadership buy-in and resource allocation
- Assign dedicated compliance owner
- Regular executive reporting

### 2. Continuous Monitoring
- Automated evidence collection where possible
- Regular control testing
- Dashboard for compliance status

### 3. Strong Documentation Culture
- Document everything as you go
- Version control for policies
- Regular policy reviews

### 4. Cross-functional Collaboration
- Security, engineering, HR, legal, operations
- Clear ownership of controls
- Regular coordination meetings

### 5. Use of Compliance Tools
- GRC platforms (Vanta, Drata, Secureframe)
- SIEM for log aggregation
- Automated vulnerability scanning
- Evidence collection automation

---

## Compliance Mapping

SOC 2 maps to other compliance frameworks:

| SOC 2 Criterion | ISO 27001 | NIST CSF | HIPAA | GDPR | PCI DSS |
|-----------------|-----------|----------|-------|------|---------|
| Security (CC)   | ✓ Full    | ✓ Full   | ✓ Full | ✓ Partial | ✓ Full |
| Availability    | ✓ Partial | ✓ Partial | ✓ Partial | - | ✓ Partial |
| Processing Integrity | ✓ Partial | ✓ Partial | ✓ Partial | ✓ Partial | ✓ Partial |
| Confidentiality | ✓ Full    | ✓ Full   | ✓ Full | ✓ Partial | ✓ Full |
| Privacy         | ✓ Partial | -        | ✓ Full | ✓ Full | ✓ Partial |

---

## Resources

### Official AICPA Resources
- [AICPA Trust Services Criteria](https://us.aicpa.org/interestareas/frc/assuranceadvisoryservices/trustdataintegritytaskforce)
- SOC 2 Implementation Guide
- Trust Services Criteria Framework

### Industry Resources
- [SOC 2 Academy](https://soc2.academy/)
- Vendor security questionnaires (SIG, CAIQ)
- Industry-specific compliance guides

### Audit Firm Resources
- Big 4 (Deloitte, PwC, EY, KPMG) SOC 2 guides
- Regional firms with SOC 2 expertise
- Compliance automation vendors (Vanta, Drata, Secureframe)

---

**Next Steps**: Review this criteria against your current state using the companion **SOC2_GAP_ASSESSMENT.md** document.


