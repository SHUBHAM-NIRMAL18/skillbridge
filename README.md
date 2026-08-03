# SkillBridge - Recruitment Management System

![tech-stack](https://skillicons.dev/icons?i=python,django,vscode,postgres,html,css,bootstrap)

![SkillBridge Logo](static/icons/sb-logo.svg)

## Description

SkillBridge is a comprehensive Recruitment Management System designed to streamline the internship and job placement process for both candidates and employers. This platform provides an intelligent, feature-rich environment for discovering opportunities, managing applications, facilitating digital offer letters, and enabling seamless asynchronous communication between job seekers and recruiters.

SkillBridge empowers organizations to post and manage job or internship openings, while allowing candidates to explore opportunities that match their skills and career goals. With its intuitive interface, AI-driven recommendation engine, and structured offer workflows, SkillBridge simplifies the entire recruitment lifecycle — from job posting to formal candidate selection.

## Key Features

### For Job Seekers / Candidates
- **Hybrid Recommendation System**: Advanced AI-powered job suggestions combining content-based filtering and collaborative filtering for personalized recommendations
- **Sector-Specific Matching**: Tailored job recommendations aligned with candidate's industry expertise and career aspirations
- **Profile Management**: Comprehensive profile creation with skills assessment, experience tracking, and resume management
- **Application Tracking & Offer Portal**: Real-time status updates on job applications, interview schedules, and digital offer letter review & acceptance
- **Advanced Search & Filters**: Find opportunities by location, salary range, company size, and job type
- **Resume Builder**: Built-in tools to create professional resumes

### For Employers / Companies
- **Digital Offer Letter Generation**: Issue formal employment and internship offer letters with customizable legal clauses, salary details, joining dates, and digital HR signatures
- **Credit-Based Job Posting**: Flexible credit system for posting job and internship opportunities
- **Membership Plans**: Various subscription tiers with different posting limits and premium features
- **Multiple Payment Options**: Seamless payment integration with Khalti and eSewa for purchasing credits
- **AJAX Applicant Drawer & Candidate Analytics**: Slide-out drawer with real-time **Skill Overlap Analytics** (matched vs. missing candidate skills), resume previews, and cover letters
- **Instant Status Management**: Asynchronously update candidate application status (`shortlisted`, `interview`, `offered`, `rejected`) via AJAX without page reloads
- **Company Branding**: Customizable company profiles to attract top talent
- **Application Analytics**: Insights into application metrics and hiring performance

### Digital Offer Letter Management System
- **Automated Offer Creation**: Generate formal offer letters directly from the candidate pipeline with pre-populated position, salary, location, and start dates
- **Pre-Configured Legal Clauses**: Built-in legal templates covering appointment hierarchy, duties, compensation, TDS tax deductions, probation period, NDA/confidentiality, IP rights, and termination notice
- **Digital Signatures & Company Seals**: Upload hiring manager digital signature images and display automated corporate verification seals
- **Candidate Acceptance Workflow**: Interactive candidate portal to accept or decline offer letters with response notes and timestamping
- **Auto-Expiration Handling**: Automatic expiration tracking for pending offer letters based on valid-until dates
- **Print & PDF Optimization**: Print-ready CSS layout supporting A4 formatting, header/footer reference codes, signature cards, and single-click PDF export

### AJAX & Real-Time Communication System
- **Asynchronous Application Submission**: Modal-based candidate application flow with live profile validation, missing resume detection, and seamless submission via AJAX
- **Dynamic Applicant Drawer**: AJAX partial rendering (`applicant_detail_partial`) allowing recruiters to inspect candidate profiles, resumes, and skill compatibility without leaving the page
- **Live Status Badges**: Recruiter status changes dynamically update row badges and application counters in real time
- **Notification & Email Trigger System**: Automated email and platform notifications sent during key events (application submission, status updates, offer letter issuance, offer acceptance/rejection)
- **Interactive Support & Feedback**: Built-in AJAX feedback submission and company support ticket messaging

### Payment & Membership System
- **Flexible Credit System**: Pay-per-post model with bulk credit packages available
- **Multiple Payment Gateways**:
  - **Khalti Integration**: Instant payment processing for Nepalese users
  - **eSewa Integration**: Alternative digital wallet payment option
  - **Bank Transfer/QR**: Traditional payment methods with receipt verification
- **Transparent Pricing**: Clear pricing structure with volume discounts
- **Instant Credit Delivery**: Immediate credit allocation upon successful payment
- **Receipt Management**: Automated receipt generation and download

### Core Platform Features
- **Dual User Interface**: Separate optimized experiences for job seekers and employers
- **Application Management**: Streamlined application process with document uploads
- **Secure Data Handling**: Enterprise-grade security for sensitive candidate and company information
- **Admin Dashboard**: Comprehensive admin panel for platform management and analytics

### Hybrid Recommendation Engine
- **Content-Based Filtering**: Matches jobs based on candidate's skills, experience, and profile attributes
- **Collaborative Filtering**: Leverages user behavior patterns and preferences of similar candidates
- **Hybrid Algorithm**: Combines both approaches for more accurate and diverse job recommendations
- **Skill-Based Matching**: Intelligent matching based on technical and soft skills alignment
- **Industry Expertise**: Sector-specific recommendations for better job-candidate fit
- **Career Growth Tracking**: Suggestions aligned with candidate's career progression goals
- **Continuous Learning**: System improves recommendations based on user interactions 

## Technology Stack
- **Backend**: Python, Django Framework
- **Database**: PostgreSQL
- **Frontend & AJAX**: HTML5, CSS3, JavaScript (Fetch / AJAX), Bootstrap 5, Bootstrap Icons
- **Payment Processing**: Khalti API, eSewa API
- **Document & PDF Handling**: Print CSS engine, Media storage for digital signatures and resumes
- **Development Environment**: Visual Studio Code
- **Recommendation System**: Hybrid Machine Learning algorithms (Content-based + Collaborative filtering)
- **Security**: CSRF protection, secure authentication, encrypted data storage, role-based access control

## Benefits

### For Candidates
- Discover highly relevant opportunities with hybrid (Collaborative + Content-based) recommendations
- Apply to jobs and internships seamlessly with modal preview and profile auto-checks
- Review, accept, or decline formal digital offer letters directly from the portal
- Track application progress in real-time with status updates
- Build professional profiles and resumes

### For Employers
- Issue legally-structured, digital offer letters complete with HR signatures and print-ready PDF export
- Review applicants faster with AJAX slide-out drawers and instant skill overlap analytics
- Cost-effective hiring with flexible credit-based pricing
- Access to a curated pool of qualified candidates
- Streamlined candidate communication and asynchronous status management

SkillBridge transforms the traditional recruitment process into an intelligent, efficient, and user-friendly experience that benefits both job seekers and employers in the modern job market.

## Docker Setup & Deployment

SkillBridge is fully containerized using Docker and Docker Compose.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### Quick Start with Docker

1. **Environment Setup**:
   Create a `.env` file in the root directory (you can copy `.env.example`):
   ```bash
   cp .env.example .env
   ```

2. **Build and Run Containers**:
   Start the application and PostgreSQL database in detached mode:
   ```bash
   docker compose up --build -d
   ```
   *The container entrypoint will automatically wait for PostgreSQL, apply database migrations, and collect static files.*

3. **Create an Admin Superuser**:
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

4. **Access the Application**:
   - Web App: [http://localhost:8000](http://localhost:8000)
   - Admin Panel: [http://localhost:8000/admin](http://localhost:8000/admin)

5. **Stop Containers**:
   ```bash
   docker compose down
   ```
