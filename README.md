AIMatchMakingTool starting code

like bare bare bones 

Steps to run:

1. Create virtual environment
python -m venv .venv (or python3)
source .venv/bin/activate

3. Install requirements
pip install -r requirements.txt

4. Export MySQL environment variables (required)
export DB_NAME=ai_matchmaking
export DB_USER=capstone_user
export DB_PASSWORD=your_mysql_password
export DB_HOST=localhost
export DB_PORT=3306
export SAM_API_KEY=your_sam_api_key_here

5. Install migrations
python manage.py migrate

and you're good!

If you want to run:
python manage.py runserver


SAM.gov sync setup

- Set `SAM_API_KEY` before running the ingest command or using the dashboard sync button.
- Example ingest command:
python manage.py ingest_sam_opportunities --limit 5
- Opportunities are saved into the `contracts_contract` table and served by `/api/opportunities/`.



How to Run the Frontend (React)

1. Navigate to the frontend folder
cd frontend/frontend 

2. Install dependencies
npm install 
(This installs all required packages.)

3. Start the development server
npm run dev 


Notes:
- This project uses a custom user model: `AUTH_USER_MODEL = 'accounts.User'`.
- `DB_PASSWORD` must be set or Django will raise a startup configuration error.
- A sample env file is provided at `.env.example`.



