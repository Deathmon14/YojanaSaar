import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SchemeCard from './SchemeCard';
import VoiceAssistant from './VoiceAssistant';
import aiAvatar from './assets/ai_avatar.jpg';
import userAvatar from './assets/user_avatar.jpg';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  // All your state variables remain the same
  const [query, setQuery] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [conversation, setConversation] = useState([]);
  const messagesEndRef = useRef(null);

  // All your functions (useEffect, handleSubmit, etc.) remain the same
  useEffect(() => {
    try {
      const savedConversation = localStorage.getItem('yojanaSaarConversation');
      if (savedConversation) setConversation(JSON.parse(savedConversation));
    } catch (e) { setConversation([]); }
  }, []);

  useEffect(() => {
    localStorage.setItem('yojanaSaarConversation', JSON.stringify(conversation));
    scrollToBottom();
  }, [conversation]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSubmit = async (queryText) => {
    if (!queryText.trim()) return;
    setLoading(true);
    setError('');
    const userMessage = { role: "user", content: queryText };
    const updatedConversation = [...conversation, userMessage];
    setConversation(updatedConversation);
    setQuery('');

    try {
      const response = await axios.post(`${API_BASE_URL}/query`, {
        user_query: queryText, k: 5, state: stateFilter || null, category: categoryFilter || null, conversation_history: updatedConversation
      });
      const modelMessage = {
        role: "model", content: response.data.answer, relevant_schemes: response.data.relevant_schemes
      };
      setConversation(prev => [...prev, modelMessage]);
    } catch (err) {
      setError('Failed to get a response from the server.');
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = () => {
    if (window.confirm("Are you sure?")) setConversation([]);
  };

  return (
    <div className="App">
      {/* --- UPDATED HEADER --- */}
      <header className="App-header">
        <div className="header-avatar">
          <img src={aiAvatar} alt="YojanaSaar AI Avatar" />
        </div>
        <div className="header-title">
          <h1>YojanaSaar AI</h1>
          <p>Your AI guide to Indian Government Schemes</p>
        </div>
      </header>

      <main className="App-main">
        <div className="conversation-area">
          {/* ... welcome message ... */}
          {conversation.length === 0 && !loading && ( <div className="welcome-message"> <p>Hello! Ask me anything about Indian government schemes.</p> </div> )}

          {conversation.map((message, index) => (
            <div key={index} className={`message-container ${message.role}`}>
              {/* --- The user avatar stays, the AI avatar is removed from here --- */}
              {message.role === 'user' && (
                <div className="avatar">
                  <img src={userAvatar} alt="user avatar" />
                </div>
              )}
              <div className={`message-bubble ${message.role}`}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                {message.role === 'model' && message.relevant_schemes?.length > 0 && (
                  <>
                    <hr style={{border: 'none', borderTop: '1px solid var(--border-color)', margin: '1rem 0'}} />
                    <div className="scheme-list">
                      {message.relevant_schemes.map((scheme, sIndex) => ( <SchemeCard key={sIndex} scheme={scheme} /> ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          ))}

          {/* --- The loading indicator is also simplified --- */}
          {loading && (
            <div className="message-container model">
              <div className="message-bubble model">
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <div className="query-section">
            <form onSubmit={(e) => { e.preventDefault(); handleSubmit(query); }} className="query-form">
              <textarea placeholder="Ask something..." value={query} onChange={(e) => setQuery(e.target.value)} rows="3" required disabled={loading}/>
              <div className="filters">
                <input type="text" placeholder="Filter by State (optional)" value={stateFilter} onChange={(e) => setStateFilter(e.target.value)} disabled={loading}/>
                <input type="text" placeholder="Filter by Category (optional)" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} disabled={loading}/>
              </div>
              <button type="submit" disabled={loading}>{loading ? 'Searching...' : 'Send'}</button>
            </form>
            {error && <div className="error-message">{error}</div>}
            <VoiceAssistant
                onVoiceInput={(voiceText) => { setQuery(voiceText); handleSubmit(voiceText); }}
                aiResponse={conversation.length > 0 ? conversation[conversation.length - 1].content : ""}
            />
        </div>
      </main>

      <aside className="history-section">
        <div className="history-controls">
            <h2>History</h2>
            {conversation.length > 0 && <button onClick={handleClearHistory} className="clear-history-button">Clear</button>}
        </div>
        <div className="history-summary">
            {conversation.length > 0 ? (
                conversation.filter(msg => msg.role === 'user').map((entry, index) => ( <div key={index} className="history-item"><p>{entry.content}</p></div> )).reverse()
            ) : ( <p style={{color: 'var(--text-secondary)', textAlign: 'center', paddingTop: '2rem'}}>No history yet.</p> )}
        </div>
      </aside>
    </div>
  );
}

export default App;