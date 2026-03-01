import { useState, useEffect, useRef } from 'react';
import { MessageCircle, X, Send, Loader2, Minimize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import api from '@/lib/api';

const generateSessionId = () => {
  return 'chat_' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
};

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    // Get or create session ID
    let storedSessionId = localStorage.getItem('chat_session_id');
    if (!storedSessionId) {
      storedSessionId = generateSessionId();
      localStorage.setItem('chat_session_id', storedSessionId);
    }
    setSessionId(storedSessionId);
    
    // Load chat history
    loadChatHistory(storedSessionId);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && !isMinimized && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen, isMinimized]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadChatHistory = async (sid) => {
    try {
      const res = await api.get(`/chat/history/${sid}`);
      if (res.data && res.data.length > 0) {
        setMessages(res.data.map(m => ({
          role: m.role,
          content: m.content
        })));
      } else {
        // Add welcome message
        setMessages([{
          role: 'assistant',
          content: "Hi! 👋 I'm your GameShop Nepal assistant. How can I help you today? I can answer questions about our products, pricing, orders, or help you find what you're looking for!"
        }]);
      }
    } catch (e) {
      // Add welcome message on error
      setMessages([{
        role: 'assistant',
        content: "Hi! 👋 I'm your GameShop Nepal assistant. How can I help you today?"
      }]);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    
    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const res = await api.post('/chat', {
        message: userMessage,
        session_id: sessionId
      });
      
      // Add AI response
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.response }]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: "Sorry, I'm having trouble connecting right now. Please try again in a moment or contact us directly!" 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const startNewChat = () => {
    const newSessionId = generateSessionId();
    localStorage.setItem('chat_session_id', newSessionId);
    setSessionId(newSessionId);
    setMessages([{
      role: 'assistant',
      content: "Hi! 👋 I'm your GameShop Nepal assistant. How can I help you today?"
    }]);
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 bg-white text-black p-4 rounded-full shadow-[0_0_40px_-10px_rgba(255,255,255,0.3)] transition-all duration-300 hover:scale-110 hover:shadow-[0_0_50px_-10px_rgba(255,255,255,0.5)] group"
        data-testid="chat-widget-toggle"
        aria-label="Open chat"
      >
        <MessageCircle className="w-6 h-6" />
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-[#30d158] rounded-full animate-pulse" />
      </button>
    );
  }

  return (
    <div 
      className={`fixed bottom-6 right-6 z-50 glass rounded-3xl shadow-2xl transition-all duration-500 ${
        isMinimized ? 'w-72 h-16' : 'w-[380px] h-[520px]'
      }`}
      data-testid="chat-widget"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center">
              <MessageCircle className="w-5 h-5 text-black" />
            </div>
            <span className="absolute bottom-0 right-0 w-3 h-3 bg-[#30d158] rounded-full border-2 border-black" />
          </div>
          <div>
            <h3 className="text-white font-semibold text-sm">GSN Support</h3>
            <p className="text-[#30d158] text-xs">Online</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-white/40 hover:text-white hover:bg-white/10 rounded-full"
            onClick={() => setIsMinimized(!isMinimized)}
            aria-label={isMinimized ? "Expand chat" : "Minimize chat"}
          >
            <Minimize2 className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-white/40 hover:text-white hover:bg-white/10 rounded-full"
            onClick={() => setIsOpen(false)}
            aria-label="Close chat"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Messages */}
          <ScrollArea className="h-[360px] p-4">
            <div className="space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] px-4 py-2 rounded-2xl ${
                      msg.role === 'user'
                        ? 'bg-amber-500 text-black rounded-br-sm'
                        : 'bg-zinc-800 text-white rounded-bl-sm'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-zinc-800 text-white px-4 py-2 rounded-2xl rounded-bl-sm">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm text-zinc-400">Typing...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Input */}
          <form onSubmit={sendMessage} className="p-4 border-t border-zinc-800">
            <div className="flex gap-2">
              <Input
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Type a message..."
                className="flex-1 bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500 rounded-full"
                disabled={isLoading}
                data-testid="chat-input"
              />
              <Button
                type="submit"
                size="icon"
                className="bg-amber-500 hover:bg-amber-600 text-black rounded-full h-10 w-10"
                disabled={isLoading || !inputMessage.trim()}
                data-testid="chat-send-btn"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
            <button
              type="button"
              onClick={startNewChat}
              className="text-xs text-zinc-500 hover:text-zinc-300 mt-2 transition-colors"
            >
              Start new conversation
            </button>
          </form>
        </>
      )}
    </div>
  );
}
