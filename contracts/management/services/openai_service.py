from openai import OpenAI
import os

# -------------------------
# CONFIG
# -------------------------
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

if not api_key:
    print("WARNING: OPENAI_API_KEY missing - using mock mode")


# -------------------------
# MOCK RESPONSE
# -------------------------
def mock_response(contract_text):
    return f"""
EXECUTIVE SUMMARY

Our company appreciates the opportunity to respond to this solicitation. Based on the provided requirements, we are positioned to deliver reliable, compliant, and high-quality services that align with agency expectations.

UNDERSTANDING OF REQUIREMENTS

We understand the agency requires a contractor capable of executing project objectives efficiently, maintaining communication, meeting deadlines, and ensuring performance accountability.

TECHNICAL APPROACH

Our team will apply structured project management practices, qualified personnel, and quality control procedures to ensure successful delivery of all required tasks and milestones.

PAST PERFORMANCE

We have experience supporting projects requiring timely execution, operational coordination, customer responsiveness, and process improvement across multiple environments.

DIFFERENTIATORS

- Strong client communication
- Efficient delivery processes
- Flexible and scalable support
- Commitment to quality assurance
- Reliable schedule performance

COMPLIANCE STATEMENT

We are committed to fulfilling all solicitation requirements, adhering to applicable regulations, and maintaining professional performance throughout the contract lifecycle.

REFERENCE SOLICITATION

{contract_text[:500]}
"""


# -------------------------
# MAIN GENERATOR
# -------------------------
def generate_rfp_response(contract_text, capability_text):

    # If no key -> mock mode
    if client is None:
        return mock_response(contract_text)

    prompt = f"""
You are a senior federal proposal writer experienced in U.S. government contracting, RFP responses, capability statements, FAR compliance, and proposal strategy.

Write a realistic, professional government proposal response using ONLY the information provided.

-----------------------------------
COMPANY CAPABILITIES
{capability_text}

-----------------------------------
Contract DETAILS
{contract_text}

-----------------------------------
INSTRUCTIONS

Write a polished response with these sections:

1. Executive Summary
2. Understanding of Requirements
3. Technical Approach
4. Relevant Experience / Past Performance
5. Key Differentiators
6. Compliance Statement

RULES:
- Formal government proposal tone
- Clear and specific writing
- Tie capabilities directly to requirements
- Do NOT invent certifications or experience
- Do NOT use marketing fluff
- Sound submission-ready
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert federal proposal writer."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4,
            max_tokens=1400
        )

        return response.choices[0].message.content

    except Exception as e:
        print("OpenAI error:", e)
        return mock_response(contract_text)