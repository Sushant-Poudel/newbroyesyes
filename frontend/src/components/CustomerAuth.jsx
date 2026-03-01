import { useState, useEffect } from 'react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Mail, KeyRound, Loader2, Phone, X } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;
const LOGO_URL = "https://customer-assets.emergentagent.com/job_8ec93a6a-4f80-4dde-b760-4bc71482fa44/artifacts/4uqt5osn_Staff.zip%20-%201.png";

// Google Icon SVG Component
const GoogleIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
  </svg>
);

export default function CustomerAuthModal({ isOpen, onClose, onSuccess }) {
  const [step, setStep] = useState('email'); // 'email' or 'otp'
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [whatsappNumber, setWhatsappNumber] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);

  const handleGoogleLogin = () => {
    // Google OAuth would be implemented here
    toast.info('Google login coming soon!');
  };

  const handleSendOTP = async (e) => {
    e.preventDefault();
    if (!email) {
      toast.error('Please enter your email');
      return;
    }
    if (!whatsappNumber) {
      toast.error('Please enter your WhatsApp number');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/auth/customer/send-otp`, {
        email: email.toLowerCase().trim(),
        name: name || email.split('@')[0],
        whatsapp_number: whatsappNumber
      });
      
      if (response.data.otp) {
        toast.success(`OTP sent! Debug mode: ${response.data.otp}`, { duration: 10000 });
      } else {
        toast.success('OTP sent to your email! Check your inbox.');
      }
      setStep('otp');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    if (!otp || otp.length !== 6) {
      toast.error('Please enter the 6-digit OTP');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/auth/customer/verify-otp`, {
        email: email.toLowerCase().trim(),
        otp: otp
      });
      
      localStorage.setItem('customer_token', response.data.token);
      localStorage.setItem('customer_info', JSON.stringify(response.data.customer));
      
      toast.success('Login successful! Welcome back 🎉');
      onSuccess && onSuccess(response.data.customer);
      onClose();
      
      setEmail('');
      setName('');
      setOtp('');
      setStep('email');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_URL}/auth/customer/send-otp`, {
        email: email.toLowerCase().trim(),
        name: name || email.split('@')[0],
        whatsapp_number: whatsappNumber
      });
      toast.success('New OTP sent!');
      setOtp('');
    } catch (error) {
      toast.error('Failed to resend OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[420px] p-0 bg-white border-0 rounded-2xl overflow-hidden" data-testid="customer-auth-modal">
        {/* Close Button */}
        <button 
          onClick={onClose}
          className="absolute right-4 top-4 text-gray-400 hover:text-gray-600 transition-colors z-10"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="p-8">
          {/* Logo */}
          <div className="flex justify-center mb-6">
            <div className="w-20 h-20 bg-[#0a0a0a] rounded-2xl flex items-center justify-center shadow-lg">
              <img src={LOGO_URL} alt="GSN" className="h-12 w-auto" />
            </div>
          </div>

          {/* Title */}
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              {step === 'email' ? 'Welcome Back' : 'Enter OTP'}
            </h2>
            <p className="text-gray-500 mt-1 text-sm">
              {step === 'email' 
                ? 'Sign in to your account'
                : `We've sent a 6-digit code to ${email}`
              }
            </p>
          </div>

          {step === 'email' ? (
            <>
              {/* Google Button */}
              <Button
                type="button"
                onClick={handleGoogleLogin}
                className="w-full bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 rounded-xl py-6 font-medium mb-6 flex items-center justify-center gap-3"
              >
                <GoogleIcon />
                Continue with Google
              </Button>

              {/* Divider */}
              <div className="relative mb-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white text-gray-400">or</span>
                </div>
              </div>

              {/* Form */}
              <form onSubmit={handleSendOTP} className="space-y-4">
                <div>
                  <Label htmlFor="email" className="text-gray-700 font-medium">Email</Label>
                  <div className="relative mt-1">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="Enter your email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="bg-gray-50 border-gray-200 text-gray-900 pl-10 h-12 rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                      required
                      data-testid="customer-email-input"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="whatsapp" className="text-gray-700 font-medium">WhatsApp Number</Label>
                  <div className="relative mt-1">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <Input
                      id="whatsapp"
                      type="tel"
                      placeholder="Enter your WhatsApp number"
                      value={whatsappNumber}
                      onChange={(e) => setWhatsappNumber(e.target.value)}
                      className="bg-gray-50 border-gray-200 text-gray-900 pl-10 h-12 rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                      required
                      data-testid="customer-whatsapp-input"
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full bg-[#1a1a1a] hover:bg-[#252525] text-white font-semibold h-12 rounded-xl mt-2"
                  disabled={loading}
                  data-testid="send-otp-button"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Sending OTP...
                    </>
                  ) : (
                    'Sign In'
                  )}
                </Button>
              </form>

              <p className="text-center text-gray-400 text-xs mt-6">
                We'll send a one-time code to your email
              </p>
            </>
          ) : (
            <form onSubmit={handleVerifyOTP} className="space-y-4">
              <div>
                <Label htmlFor="otp" className="text-gray-700 font-medium">Enter OTP</Label>
                <div className="relative mt-1">
                  <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    id="otp"
                    type="text"
                    placeholder="Enter 6-digit code"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    className="bg-gray-50 border-gray-200 text-gray-900 pl-10 h-12 rounded-xl text-center text-xl font-mono tracking-widest focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                    maxLength={6}
                    required
                    data-testid="otp-input"
                    autoFocus
                  />
                </div>
                <p className="text-xs text-gray-400 mt-2 text-center">
                  Code expires in 10 minutes
                </p>
              </div>

              <Button
                type="submit"
                className="w-full bg-[#1a1a1a] hover:bg-[#252525] text-white font-semibold h-12 rounded-xl"
                disabled={loading || otp.length !== 6}
                data-testid="verify-otp-button"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  'Verify & Login'
                )}
              </Button>

              <div className="flex items-center justify-between text-sm pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setStep('email');
                    setOtp('');
                  }}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ← Change Email
                </button>
                <button
                  type="button"
                  onClick={handleResendOTP}
                  disabled={loading}
                  className="text-amber-600 hover:text-amber-700 font-medium disabled:opacity-50"
                >
                  Resend OTP
                </button>
              </div>
            </form>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Hook to check if customer is logged in
export function useCustomerAuth() {
  const [customer, setCustomer] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('customer_token');
    const customerInfo = localStorage.getItem('customer_info');
    
    if (token && customerInfo) {
      try {
        setCustomer(JSON.parse(customerInfo));
      } catch (e) {
        localStorage.removeItem('customer_token');
        localStorage.removeItem('customer_info');
      }
    }
    setIsLoading(false);
  }, []);

  const logout = () => {
    localStorage.removeItem('customer_token');
    localStorage.removeItem('customer_info');
    setCustomer(null);
    toast.success('Logged out successfully');
  };

  const login = (customerData) => {
    setCustomer(customerData);
  };

  return { customer, isLoading, logout, login, isAuthenticated: !!customer };
}
