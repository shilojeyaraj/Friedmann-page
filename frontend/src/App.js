import React, { useState } from 'react';
import axios from 'axios';
import './business-theme.css'; // Place your CSS here

function App() {
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    income: '',
    risk_tolerance: 'Low',
    financial_goals: ''
  });

  const [proposal, setProposal] = useState('');

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post('http://localhost:8000/api/proposal', formData);
      setProposal(res.data.proposal);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="container">
      <h1>Financial Proposal Generator</h1>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Name</label>
          <input type="text" name="name" className="form-control" onChange={handleChange} />
        </div>
        <div className="form-group">
          <label>Age</label>
          <input type="number" name="age" className="form-control" onChange={handleChange} />
        </div>
        <div className="form-group">
          <label>Income</label>
          <input type="number" name="income" className="form-control" onChange={handleChange} />
        </div>
        <div className="form-group">
          <label>Risk Tolerance</label>
          <select name="risk_tolerance" className="form-control" onChange={handleChange}>
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
          </select>
        </div>
        <div className="form-group">
          <label>Financial Goals</label>
          <textarea name="financial_goals" className="form-control" onChange={handleChange}></textarea>
        </div>
        <button type="submit" className="btn btn-primary">Generate Proposal</button>
      </form>
      {proposal && (
        <div className="card mt-4">
          <div className="card-body">
            <h5 className="card-title">Generated Proposal</h5>
            <p className="card-text">{proposal}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
