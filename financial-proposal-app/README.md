# Financial Proposal App

This project is a Financial Proposal Generator application that consists of a backend built with FastAPI and a frontend developed using React. The application allows users to interact with financial documents and retrieve information through a chat interface.

## Project Structure

The project is organized into two main directories: `backend` and `frontend`.

### Backend

- **`main.py`**: Contains the FastAPI application setup, including the initialization of a Supabase client, loading PDF documents, creating a vector store for document retrieval, and defining API endpoints for chat functionality.
- **`requirements.txt`**: Lists the Python dependencies required for the backend application, such as FastAPI, Supabase, Langchain, and any other necessary libraries.
- **`README.md`**: Provides documentation for the backend, including setup instructions, usage, and any relevant information about the API.

### Frontend

- **`public/index.html`**: The main HTML file for the frontend application. It serves as the entry point for the React application and includes links to styles and scripts.
- **`src/App.tsx`**: The main component of the React application. It sets up the application structure and includes routing if necessary.
- **`src/index.tsx`**: The entry point for the React application. It renders the `App` component into the DOM.
- **`src/components/ChatBox.tsx`**: Exports a `ChatBox` component that handles user input and displays chat messages. It interacts with the backend API to send and receive messages.
- **`src/components/Header.tsx`**: Exports a `Header` component that displays the application title and navigation links, contributing to the business-themed layout.
- **`src/styles/business-theme.css`**: Contains CSS styles that define the business-themed design for the frontend application, including colors, fonts, and layout styles.
- **`package.json`**: The configuration file for npm. It lists the dependencies, scripts, and metadata for the frontend React application.
- **`README.md`**: Provides documentation for the frontend, including setup instructions, usage, and any relevant information about the components and styling.

## Setup Instructions

### Backend

1. Navigate to the `backend` directory.
2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Set up your environment variables for Supabase in a `.env` file.
4. Run the FastAPI application:
   ```
   uvicorn main:app --reload
   ```

### Frontend

1. Navigate to the `frontend` directory.
2. Install the required npm packages:
   ```
   npm install
   ```
3. Start the React application:
   ```
   npm start
   ```

## Usage

- Access the backend API at `http://localhost:8000`.
- Access the frontend application at `http://localhost:3000`.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.