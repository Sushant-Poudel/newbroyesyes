import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AuthCallback() {
  const navigate = useNavigate();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processCallback = async () => {
      try {
        // Extract session_id from URL fragment
        const hash = window.location.hash;
        const sessionIdMatch = hash.match(/session_id=([^&]+)/);
        
        if (!sessionIdMatch) {
          toast.error('Authentication failed - no session found');
          navigate('/');
          return;
        }

        const sessionId = sessionIdMatch[1];

        // Call backend to exchange session_id for user data
        const response = await axios.post(`${API_URL}/auth/google/callback`, {
          session_id: sessionId
        });

        if (response.data.success) {
          // Store customer info
          localStorage.setItem('customer_token', response.data.token);
          localStorage.setItem('customer_info', JSON.stringify(response.data.customer));
          
          toast.success(`Welcome, ${response.data.customer.name || 'User'}!`);
          
          // Redirect to home page
          navigate('/');
        } else {
          throw new Error(response.data.error || 'Authentication failed');
        }
      } catch (error) {
        console.error('Auth callback error:', error);
        toast.error(error.response?.data?.detail || 'Authentication failed. Please try again.');
        navigate('/');
      }
    };

    processCallback();
  }, [navigate]);

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin text-amber-500 mx-auto mb-4" />
        <p className="text-white/70 text-lg">Completing sign in...</p>
        <p className="text-white/40 text-sm mt-2">Please wait while we authenticate you</p>
      </div>
    </div>
  );
}
