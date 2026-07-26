import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageCircle, 
  LayoutDashboard, 
  Send,
  AlertTriangle,
  MessageSquare,
  Check,
  Phone,
  MoreVertical,
  Clock,
  Activity,
  Search,
  Sparkles,
  ToggleLeft,
  ToggleRight,
  ArrowRight,
  RotateCcw,
  Users,
  X
} from 'lucide-react';

import './index.css';

const QUICK_PROMPTS = [
  "🦷 عروض تنظيف الأسنان وآثار السجاير",
  "🎯 معاينة النتيجة 3D قبل الشغل",
  "📅 حجز موعد كشف وحشو عصب",
  "🚨 ألم شديد جداً وضرس وارم (طوارئ)",
  "🦷 أسعار طربوش الزيركون والتقويم"
];

function App() {
  const [view, setView] = useState('simulator');
  const [resetKey, setResetKey] = useState(0);

  const handleResetDemo = async () => {
    try {
      localStorage.clear();
      await fetch('/api/reset', { method: 'POST' });
      setResetKey(prev => prev + 1);
    } catch (e) {}
  };



  return (
    <div className="app-layout" dir="rtl">
      <header className="main-header">
        <div className="header-brand">
          <img src="/logo.jpg" alt="عيادة د. العقباوي لطب الأسنان" className="official-clinic-logo" />
          <div className="brand-titles">
            <h1>Al-Aqabawi Clinic</h1>
            <span className="subtitle">منصة إدارة العمليات والاستقبال الذكي - الشروق</span>
          </div>

        </div>

        <div className="header-actions">
          <button className="btn-reset-demo" onClick={handleResetDemo} title="إعادة ضبط التجربة">
            <RotateCcw size={18} />
            <span className="btn-text">إعادة ضبط التجربة (Reset)</span>
          </button>
          
          <div className="system-status-chip">
            <span className="pulse-dot"></span>
            <span className="chip-text">النظام الذكي: نشط 🟢</span>
          </div>
          <div className="view-toggle">
            <button 
              className={`toggle-btn ${view === 'simulator' ? 'active' : ''}`}
              onClick={() => setView('simulator')}
              title="شات الواتساب"
            >
              <MessageCircle size={20} />
              <span className="btn-text">شات الواتساب</span>
            </button>
            <button 
              className={`toggle-btn ${view === 'admin' ? 'active' : ''}`}
              onClick={() => setView('admin')}
              title="لوحة الإدارة والعمليات"
            >
              <LayoutDashboard size={20} />
              <span className="btn-text">لوحة الإدارة</span>
            </button>
          </div>
        </div>

      </header>
      
      <main className="main-content" key={resetKey}>
        {view === 'simulator' ? <WhatsAppSimulator /> : <AdminDashboard />}
      </main>
    </div>
  );
}

function WhatsAppSimulator() {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('clinic_chat_messages_v1');
    return saved ? JSON.parse(saved) : [];
  });
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  // Sync to local storage
  useEffect(() => {
    localStorage.setItem('clinic_chat_messages_v1', JSON.stringify(messages));
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Fetch messages on mount & periodic polling
  useEffect(() => {
    const fetchMsgs = () => {
      fetch('/api/conversations/thread-1/messages')
        .then(res => res.json())
        .then(data => {
          if (data.messages) {
            setMessages(data.messages.map(m => ({
              id: m.id,
              text: m.text,
              sender: m.sender === 'user' ? 'user' : 'bot',
              time: m.timestamp ? m.timestamp.split(' ')[1] || 'الآن' : 'الآن'
            })));
          }
        })
        .catch(() => {});
    };

    fetchMsgs();
    const interval = setInterval(fetchMsgs, 2500);
    return () => clearInterval(interval);
  }, []);


  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (text) => {
    if (!text.trim()) return;
    
    const newUserMsg = {
      id: Date.now(),
      text,
      sender: 'user',
      time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
    };
    
    setMessages(prev => [...prev, newUserMsg]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, thread_id: "thread-1" })
      });
      
      let botReply = "عفواً، حدث خطأ في الاتصال بالنظام.";
      if (response.ok) {
        const data = await response.json();
        botReply = data.reply || data.response || "تم استلام رسالتك.";
      }
      
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: botReply,
        sender: 'bot',
        time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: "عفواً، لا يمكن الاتصال بالخادم الآن.",
        sender: 'bot',
        time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="wa-full-chat" dir="rtl">
      <div className="wa-header">
        <div className="wa-header-left">
          <img src="/logo.jpg" alt="العقباوي" className="wa-avatar-img" />

          <div className="wa-contact-info">
            <h2>عيادة د. العقباوي لطب الأسنان</h2>
            <span>{isTyping ? 'جاري الكتابة...' : 'متصل الآن (خدمة الاستقبال الذكية)'}</span>
          </div>
        </div>
        <div className="wa-header-right">
          <Phone size={20} />
          <MoreVertical size={20} />
        </div>
      </div>
      
      <div className="wa-chat-area">
        <div className="wa-date-badge">اليوم</div>
        {messages.map((msg) => (
          <div key={msg.id} className={`wa-bubble-wrapper ${msg.sender}`}>
            <div className={`wa-bubble ${msg.sender}`}>
              <p className="wa-text">{msg.text}</p>
              <span className="wa-time">
                {msg.time}
                {msg.sender === 'user' && <Check size={14} className="wa-read-tick" />}
              </span>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="wa-bubble-wrapper bot">
            <div className="wa-bubble bot typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="wa-quick-prompts">
        {QUICK_PROMPTS.map((prompt, idx) => (
          <button key={idx} onClick={() => handleSend(prompt)} className="wa-chip">
            {prompt}
          </button>
        ))}
      </div>

      <div className="wa-input-area">
        <div className="wa-input-wrapper">
          <input 
            type="text" 
            placeholder="اكتب رسالتك هنا..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend(input)}
            dir="auto"
          />
        </div>
        <button className="wa-send-btn-gold" onClick={() => handleSend(input)}>
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}

function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('conversations'); // Default to Client Conversations

  return (
    <div className="admin-container-nuit" dir="rtl">
      <div className="admin-workspace">
        <nav className="sidebar-nav-nuit">
          <div className="sidebar-section-lbl">عمليات النظام الذكي</div>
          <button 
            className={`nav-item-nuit ${activeTab === 'conversations' ? 'active' : ''}`}
            onClick={() => setActiveTab('conversations')}
          >
            <MessageSquare size={18} />
            <span>محادثات المرضى المباشرة</span>
          </button>

          <button 
            className={`nav-item-nuit ${activeTab === 'tickets' ? 'active' : ''}`}
            onClick={() => setActiveTab('tickets')}
          >
            <AlertTriangle size={18} />
            <span>مركز تذاكر التصعيد والطوارئ</span>
            <span className="badge-count">2</span>
          </button>

          <button 
            className={`nav-item-nuit ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <Activity size={18} />
            <span>لوحة الأداء العام</span>
          </button>
        </nav>

        <div className="admin-body-nuit">
          {activeTab === 'conversations' && <ClientConversationsTab />}
          {activeTab === 'tickets' && <EscalationTicketsTab onNavigateToConversations={() => setActiveTab('conversations')} />}
          {activeTab === 'overview' && <OverviewTab />}
        </div>
      </div>
    </div>
  );
}

/* === TAB 1: OVERVIEW DASHBOARD === */
function OverviewTab() {
  return (
    <div className="nuit-overview-pane">
      <div className="nuit-section-group">
        <div className="nuit-group-header">المؤشرات الرئيسية — أداء اليوم</div>
        <div className="metrics-row-nuit">
          <div className="metric-box-nuit">
            <span className="lbl">معدل التوجيه التلقائي</span>
            <span className="val">84%</span>
            <span className="sub">تم التعامل معها بدون تدخل بشري</span>
          </div>
          <div className="metric-box-nuit">
            <span className="lbl">متوسط سرعة الإجابة</span>
            <span className="val">5.2s</span>
            <span className="sub">زمن الاستجابة التلقائية</span>
          </div>

          <div className="metric-box-nuit">
            <span className="lbl">التوفير التقديري للعمالة</span>
            <span className="val">450 جنيه</span>
            <span className="sub">مقارنة بالموظف البشري</span>
          </div>
          <div className="metric-box-nuit">
            <span className="lbl">معدل المزامنة بالنظام</span>
            <span className="val">100%</span>
            <span className="sub">جميع الجلسات مسجلة</span>
          </div>
        </div>
      </div>

      <div className="nuit-section-group">
        <div className="nuit-group-header">تطور المحادثات والطلب خلال الأسبوع</div>
        <div className="charts-row-nuit">
          <div className="chart-box-nuit">
            <h3>اتجاهات المحادثات الأسبوعية</h3>
            <p className="sub-txt">مقارنة التواصل التلقائي والتحويل البشري حسب اليوم</p>
            <div className="bars-chart">
              {['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'].map((day, idx) => (
                <div key={idx} className="bar-group">
                  <div className="bars-container">
                    <div className="bar-main" style={{ height: `${[70, 85, 40, 90, 60, 20, 50][idx]}%` }}></div>
                    {idx === 3 && <div className="bar-handoff" style={{ height: '25%' }}></div>}
                  </div>
                  <span className="day-lbl">{day}</span>
                </div>
              ))}
            </div>
            <div className="chart-legend">
              <span><span className="dot orange"></span> إجمالي تواصل المرضى</span>
              <span><span className="dot blue"></span> التحويل للموظف البشري</span>
            </div>
          </div>

          <div className="sentiment-box-nuit">
            <h3>المزاج العام وانطباع المرضى</h3>
            <p className="sub-txt">تحليل الحالة النفسية من السلبية للإيجابية</p>
            
            <div className="sentiment-bar-gradient"></div>

            <div className="sentiment-list">
              <div className="sent-row"><span>ممتاز ورضا تام</span><span className="font-bold">25%</span></div>
              <div className="sent-row"><span>استفسارات عامة هادئة</span><span className="font-bold">65%</span></div>
              <div className="sent-row"><span>قلق قبل العلاج</span><span className="font-bold">5%</span></div>
              <div className="sent-row"><span>ألم شديد وتورم</span><span className="font-bold">5%</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* === TAB 2: CLIENT CONVERSATIONS === */
function ClientConversationsTab() {
  const [threads, setThreads] = useState([
    { id: 'thread-1', patient: 'شات الواتساب المباشر', phone: '01012345678', lastMsg: 'عايزة أعرف عرض تنظيف الأسنان بكام؟', status: 'نشط', rawStatus: 'ACTIVE', time: '09:21 ص', vibe: 'استفسارات عامة', topic: 'عرض تنظيف الأسنان' },
    { id: 'thread-2', patient: 'محمود علي', phone: '01099887766', lastMsg: 'ألم شديد جداً وتورم في الضرس السفلي', status: 'مُصعّد', rawStatus: 'ESCALATED', time: '10:15 ص', vibe: 'ألم شديد وتورم', topic: 'طوارئ ألم حادة' },
    { id: 'thread-3', patient: 'حبيبة خالد', phone: '01198765432', status: 'مُستلم', rawStatus: 'CLAIMED', time: '07:36 ص', lastMsg: 'أنا بعتت رسالة ومستنية الدكتور يكلمني', vibe: 'قلق وتأكيد موعد', topic: 'تعديل موعد' }
  ]);
  const [selectedThreadId, setSelectedThreadId] = useState('thread-1');
  const [messages, setMessages] = useState([]);
  const [manualInput, setManualInput] = useState('');
  const [aiEnabled, setAiEnabled] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [isThreadsModalOpen, setIsThreadsModalOpen] = useState(false);
  const [mobileActivePane, setMobileActivePane] = useState('list'); // 'list' or 'chat'

  const activeThread = threads.find(t => t.id === selectedThreadId) || threads[0];



  // Poll conversations list from backend
  useEffect(() => {
    const fetchThreads = () => {
      fetch('/api/conversations')
        .then(res => res.json())
        .then(data => {
          if (data.conversations && data.conversations.length > 0) {
            const mapped = data.conversations.map(c => ({
              id: c.thread_id,
              patient: c.thread_id === 'thread-1' ? 'شات الواتساب المباشر' : (c.patient_name || 'مريض الشات'),
              phone: c.patient_phone || '01012345678',
              lastMsg: c.last_message || 'محادثة جارية',
              status: c.ai_enabled ? 'نشط' : (c.status === 'escalated' ? 'مُصعّد' : 'تحكم بشري'),
              rawStatus: c.ai_enabled ? 'ACTIVE' : (c.status === 'escalated' ? 'ESCALATED' : 'MANUAL'),
              time: c.updated_at ? c.updated_at.split(' ')[1] || 'الآن' : 'الآن',
              vibe: c.sentiment || 'استفسارات عامة',
              topic: 'محادثة الواتساب الحية'
            }));
            setThreads(mapped);
          }
        })
        .catch(() => {});
    };

    fetchThreads();
    const interval = setInterval(fetchThreads, 3000);
    return () => clearInterval(interval);
  }, []);

  // Poll messages for selected thread
  useEffect(() => {
    const fetchMsgs = () => {
      fetch(`/api/conversations/${selectedThreadId}/messages`)
        .then(res => res.json())
        .then(data => {
          if (data.messages) {
            setMessages(data.messages);
          }
        })
        .catch(() => {});
    };

    fetchMsgs();
    const interval = setInterval(fetchMsgs, 2000);
    return () => clearInterval(interval);
  }, [selectedThreadId]);

  const handleToggleAi = async () => {
    const nextState = aiEnabled === 1 ? 0 : 1;
    setAiEnabled(nextState);
    try {
      await fetch(`/api/conversations/${selectedThreadId}/toggle_ai`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: nextState })
      });
      setThreads(prev => prev.map(t => t.id === selectedThreadId ? { ...t, status: nextState ? 'نشط' : 'تحكم بشري', rawStatus: nextState ? 'ACTIVE' : 'MANUAL' } : t));
    } catch (e) {}
  };

  const handleSendManual = async () => {
    if (!manualInput.trim()) return;
    const txt = manualInput;
    setManualInput('');
    setMessages(prev => [...prev, { thread_id: selectedThreadId, sender: 'human', text: txt, timestamp: 'الآن' }]);
    
    try {
      await fetch(`/api/conversations/${selectedThreadId}/manual_reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: txt })
      });
    } catch (e) {}
  };

  return (
    <div className="nuit-3col-conversations" data-mobile-pane={mobileActivePane} dir="rtl">
      {/* COLUMN 1: LEFT THREAD LIST */}
      <div className="col-threads-list">
        <div className="search-box-nuit">
          <Search size={16} />
          <input 
            type="text" 
            placeholder="البحث برقم المريض، الاسم..." 
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="threads-scroll-list">
          {threads.map(t => (
            <div 
              key={t.id} 
              className={`thread-item-card ${t.id === selectedThreadId ? 'selected' : ''}`}
              onClick={() => { 
                setSelectedThreadId(t.id); 
                setAiEnabled(t.rawStatus === 'ACTIVE' ? 1 : 0);
                setMobileActivePane('chat'); 
              }}
            >
              <div className="thread-item-top">
                <span className="patient-name">{t.patient}</span>
                <span className="thread-time">{t.time}</span>
              </div>
              <p className="thread-snippet">{t.lastMsg}</p>
              <div className="thread-pills">
                <span className={`pill-status ${t.rawStatus.toLowerCase()}`}>{t.status}</span>
                <span className="pill-channel">واتساب</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* COLUMN 2: CENTER LIVE CHAT & HUMAN TAKEOVER BAR */}
      <div className="col-center-chat">
        <div className="chat-center-header">
          <button className="btn-mobile-back" onClick={() => setMobileActivePane('list')} title="العودة لقائمة المحادثات">
            <ArrowRight size={16} />
            <span>المحادثات</span>
          </button>

          <div className="patient-header-info">
            <h2>{activeThread.patient}</h2>
            <span className="sub-info">واتساب • {activeThread.phone}</span>
          </div>

          <button className={`btn-takeover ${aiEnabled ? 'ai-active' : 'human-takeover'}`} onClick={handleToggleAi}>
            {aiEnabled ? (
              <><span>البوت الذكي (نشط)</span> <ToggleRight size={18}/></>
            ) : (
              <><span>التحكم البشري (نشط)</span> <ToggleLeft size={18}/></>
            )}
          </button>
        </div>




        <div className="chat-messages-scroll">
          {messages.map((m, idx) => (
            <div key={idx} className={`nuit-msg-bubble-wrapper ${m.sender}`}>
              <div className={`nuit-msg-bubble ${m.sender}`}>
                <div className="msg-sender-tag">{m.sender === 'user' ? activeThread.patient : m.sender === 'human' ? 'موظف الاستقبال البشري 👨‍⚕️' : 'المساعد الذكي للعيادة 🤖'}</div>
                <p>{m.text}</p>
                <span className="msg-time">{m.timestamp || '06:21 ص'}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="manual-input-bar">
          <input 
            type="text" 
            placeholder={aiEnabled ? "اكتب رداً يدويًا (سيتم تحويل التحكم للبشر فوراً)..." : "اكتب رداً يدويًا للمريض..."}
            value={manualInput}
            onChange={e => setManualInput(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && handleSendManual()}
          />
          <button className="btn-send-manual" onClick={handleSendManual}>
            <span>إرسال</span> <Send size={16} />
          </button>
        </div>
      </div>

      {/* COLUMN 3: RIGHT CLIENT PROFILE & METRICS */}
      <div className="col-right-profile">
        <div className="profile-section-title">ملف بيانات المريض</div>
        <div className="profile-field-row">
          <span className="lbl">اسم المريض</span>
          <span className="val font-bold">{activeThread.patient}</span>
        </div>
        <div className="profile-field-row">
          <span className="lbl">رقم الموبايل</span>
          <span className="val">{activeThread.phone}</span>
        </div>
        <div className="profile-field-row">
          <span className="lbl">قناة التواصل</span>
          <span className="val">واتساب</span>
        </div>
        <div className="profile-field-row">
          <span className="lbl">الانطباع العام</span>
          <span className="val gold-text font-bold">{activeThread.vibe}</span>
        </div>
        <div className="profile-field-row">
          <span className="lbl">تصنيف الاستفسار</span>
          <span className="val">{activeThread.topic}</span>
        </div>

        <div className="profile-divider"></div>

        <div className="profile-section-title">مؤشرات استهلاك الذكاء الاصطناعي</div>
        <div className="profile-field-row">
          <span className="lbl">توكنز المدخلات</span>
          <span className="val">1,209</span>
        </div>
        <div className="profile-field-row">
          <span className="lbl">توكنز المخرجات</span>
          <span className="val">432</span>
        </div>
        <div className="profile-field-row">
          <span className="lbl">التكلفة المحسوبة</span>
          <span className="val gold-text">$0.00078</span>
        </div>

        <div className="profile-divider"></div>

        <div className="profile-section-title">سجل التدقيق والمزامنة</div>
        <div className="audit-box-info">
          <p>المزامنة: قناة المزامنة نشطة عبر الواتساب</p>
          <p>الحالة: {aiEnabled ? 'المحادثة نشطة (البوت يعمل تلقائياً)' : 'التحكم البشري نشط (البوت متوقف مؤقتاً)'}</p>
        </div>
      </div>

      {/* POP-UP MODAL WINDOW FOR SELECTING CLIENT CHATS */}
      {isThreadsModalOpen && (
        <div className="modal-backdrop-threads" onClick={() => setIsThreadsModalOpen(false)}>
          <div className="modal-threads-card" onClick={e => e.stopPropagation()} dir="rtl">
            <div className="modal-threads-header">
              <div className="m-title">
                <Users size={18} />
                <h3>اختر محادثة المريض</h3>
              </div>
              <button className="btn-close-modal" onClick={() => setIsThreadsModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="search-box-nuit">
              <Search size={16} />
              <input 
                type="text" 
                placeholder="البحث برقم المريض، الاسم..." 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="modal-threads-scroll">
              {threads
                .filter(t => !searchQuery || t.patient.includes(searchQuery) || t.phone.includes(searchQuery) || t.lastMsg.includes(searchQuery))
                .map(t => (
                  <div 
                    key={t.id} 
                    className={`thread-item-card ${t.id === selectedThreadId ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedThreadId(t.id);
                      setAiEnabled(t.rawStatus === 'ACTIVE' ? 1 : 0);
                      setIsThreadsModalOpen(false);
                    }}
                  >
                    <div className="thread-item-top">
                      <span className="patient-name">{t.patient}</span>
                      <span className="thread-time">{t.time}</span>
                    </div>
                    <p className="thread-snippet">{t.lastMsg}</p>
                    <div className="thread-pills">
                      <span className={`pill-status ${t.rawStatus.toLowerCase()}`}>{t.status}</span>
                      <span className="pill-channel">واتساب</span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


/* === TAB 3: ESCALATION TICKETS === */
function EscalationTicketsTab({ onNavigateToConversations }) {
  const [tickets, setTickets] = useState([
    { id: 1, thread_id: 'thread-2', patient: 'محمود علي', phone: '01099887766', issue: 'ألم شديد جداً وتورم في الضرس السفلي لا يستجيب للمسكنات ويحتاج طبيب طوارئ', status: 'مفتوحة', rawStatus: 'OPEN', urgency: 'حرج للغاية', time: 'منذ 8 دقائق', action: 'تحويل الحجز لطبيب الطوارئ أو الاستجابة السريعة وتسكين الألم.' },
    { id: 2, thread_id: 'thread-3', patient: 'حبيبة خالد', phone: '01198765432', issue: 'طلب تغيير موعد ومتابعة مع د. إبراهيم جمال', status: 'مُستلمة', rawStatus: 'CLAIMED', urgency: 'عاجل', time: 'منذ 25 دقيقة', action: 'مراجعة أوقات د. إبراهيم وتعديل الموعد' }
  ]);
  const [selectedTicketId, setSelectedTicketId] = useState(1);
  const [ticketFilter, setTicketFilter] = useState('ALL');

  useEffect(() => {
    const fetchTickets = () => {
      fetch('/api/tickets')
        .then(res => res.json())
        .then(data => {
          if (data.tickets && data.tickets.length > 0) {
            const mapped = data.tickets.map(t => ({
              id: t.id,
              thread_id: t.conversation_id || 'thread-1',
              patient: t.conversation_id === 'thread-1' ? 'شات الواتساب المباشر' : (t.patient_name || 'مريض الشات'),
              phone: t.customer_phone || '01012345678',
              issue: t.summary || 'طلب تدخل بشري وطوارئ',
              status: t.status === 'open' ? 'مفتوحة' : (t.status === 'claimed' ? 'مُستلمة' : 'تم الحل'),
              rawStatus: (t.status || 'open').toUpperCase(),
              urgency: t.urgency > 0.8 ? 'حرج للغاية' : 'عاجل',
              time: t.created_at ? t.created_at.split(' ')[1] || 'الآن' : 'الآن',
              action: 'التواصل المباشر مع المريض وتسكين المشكلة أو الشكوى.'
            }));
            setTickets(mapped);
          }
        })
        .catch(() => {});
    };

    fetchTickets();
    const interval = setInterval(fetchTickets, 2500);
    return () => clearInterval(interval);
  }, []);

  const selectedTicket = tickets.find(t => t.id === selectedTicketId) || tickets[0];


  const handleUpdateTicket = async (id, status, statusAr) => {
    setTickets(prev => prev.map(t => t.id === id ? { ...t, status: statusAr, rawStatus: status } : t));
    try {
      await fetch(`/api/tickets/${id}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: status.toLowerCase() })
      });
    } catch (e) {}
  };

  const filteredTickets = ticketFilter === 'ALL' 
    ? tickets 
    : tickets.filter(t => t.rawStatus === ticketFilter);

  return (
    <div className="nuit-tickets-view" dir="rtl">
      {/* TOP STAT COUNTERS */}
      <div className="ticket-stats-header">
        <div className="ticket-stat-card">
          <span className="num danger">{tickets.filter(t => t.rawStatus === 'OPEN').length}</span>
          <span className="lbl">تذاكر مفتوحة (تطلب متابعة)</span>
        </div>
        <div className="ticket-stat-card">
          <span className="num warning">{tickets.filter(t => t.rawStatus === 'CLAIMED').length}</span>
          <span className="lbl">جاري التعامل معها</span>
        </div>
        <div className="ticket-stat-card">
          <span className="num success">{tickets.filter(t => t.rawStatus === 'RESOLVED').length}</span>
          <span className="lbl">تم الحل والإغلاق</span>
        </div>
        <div className="ticket-stat-card">
          <span className="num">{tickets.length}</span>
          <span className="lbl">إجمالي حالات التصعيد</span>
        </div>
      </div>

      <div className="tickets-main-split">
        {/* LEFT TICKETS FILTER LIST */}
        <div className="col-tickets-list">
          <div className="filter-tabs-tickets">
            {[
              { id: 'ALL', label: 'الكل' },
              { id: 'OPEN', label: 'مفتوحة' },
              { id: 'CLAIMED', label: 'مستلمة' },
              { id: 'RESOLVED', label: 'تم الحل' }
            ].map(f => (
              <button 
                key={f.id} 
                className={`t-filter-btn ${ticketFilter === f.id ? 'active' : ''}`}
                onClick={() => setTicketFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="tickets-scroll-stack">
            {filteredTickets.map(t => (
              <div 
                key={t.id} 
                className={`ticket-list-card ${t.id === selectedTicketId ? 'selected' : ''}`}
                onClick={() => setSelectedTicketId(t.id)}
              >
                <div className="t-card-top">
                  <span className={`pill-status ${t.rawStatus.toLowerCase()}`}>{t.status}</span>
                  <span className="t-id">تذكرة #{t.id}</span>
                </div>
                <h4>{t.patient}</h4>
                <p className="t-snippet">{t.issue}</p>
                <span className="t-phone-sub">{t.phone} • {t.time}</span>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT TICKET DETAIL PANE */}
        <div className="col-ticket-detail">
          <div className="ticket-detail-head">
            <h2>تذكرة رقم #{selectedTicket.id} <span className={`pill-status ${selectedTicket.rawStatus.toLowerCase()}`}>{selectedTicket.status}</span></h2>
            <div className="ticket-meta-line">
              <span>📱 {selectedTicket.phone}</span>
              <span>• المحادثة: {selectedTicket.thread_id}</span>
              <span>• فُتحت {selectedTicket.time}</span>
            </div>
          </div>

          <div className="ticket-statement-box">
            <div className="box-title">بيان مشكلة المريض</div>
            <p>{selectedTicket.issue}</p>
          </div>

          <div className="ai-recommendation-box">
            <div className="box-title"><Sparkles size={16}/> الإجراء الموصى به من النظام الذكي</div>
            <p>{selectedTicket.action}</p>
          </div>

          <div className="ticket-action-footer">
            <button className="btn-takeover-large" onClick={onNavigateToConversations}>
              <span>فتح المحادثة والتحكم المباشر في شات المرضى</span> <ArrowRight size={18}/>
            </button>

            {selectedTicket.rawStatus !== 'RESOLVED' ? (
              <button className="btn-resolve-ticket" onClick={() => handleUpdateTicket(selectedTicket.id, 'RESOLVED', 'تم الحل')}>
                <Check size={16}/> تحديد كـ تم الحل (إغلاق التذكرة وإعادة البوت)
              </button>
            ) : (
              <span className="resolved-done-txt">✓ تم حل التذكرة وإعادة تفعيل البوت</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
