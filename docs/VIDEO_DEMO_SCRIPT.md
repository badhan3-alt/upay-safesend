# Upay SafeSend — Video Demonstration Script (2–3 Minutes)
### AI DEV FEST 2026 — DIU CPC × upay Hackathon

---

### **[0:00 - 0:25] Opening & Problem Statement**
**Speaker:**
> *"Upay SafeSend is an AI-powered transaction guardian designed to protect mobile financial service users from suspicious and potentially fraudulent transactions.*
> 
> *In Bangladesh today, mobile wallet fraud and social engineering scams cause millions of takas in losses every month. Traditional fraud detection works after the fact—when the money has already left the wallet and been withdrawn through cash-out agents. SafeSend changes this completely by intercepting transactions before they occur."*

---

### **[0:25 - 0:50] The Mobile Experience: Normal vs. High-Risk**
*(Screen recording showing the simulated mobile app at `http://127.0.0.1:8000/`)*

**Speaker:**
> *"Here is our simulated Upay mobile wallet interface. Let's demonstrate two scenarios.*
> 
> *First, a normal transaction: User U0001 sends ৳1,500 to a regular contact during daytime. SafeSend evaluates 9 behavioral features in milliseconds. The risk score is only 6%—Low Risk. The transfer is confirmed instantly with zero user friction.*
> 
> *Now, let's test a dangerous scam scenario: using our 1-click demo preset, the user attempts to send ৳38,500 at 3:00 AM to a new recipient from a changed device."*

---

### **[0:50 - 1:25] Pre-Transaction Interception & Explainable AI (SHAP)**
*(Screen recording transitions to `/warning/` showing the red high-risk alert and SHAP bars)*

**Speaker:**
> *"Immediately, SafeSend intervenes before the funds are sent.*
> 
> *Instead of an annoying generic error message, SafeSend provides explainable intelligence: An AI Risk Score of 93%—High Risk. The Anomaly Detection engine flags this as an abnormal outflow.*
> 
> *Notice our SHAP explainability section: it shows the exact mathematical contribution of each signal—the massive amount ratio and unfamiliar recipient drove the risk up.*
> 
> *And crucially for Bangladesh, SafeSend features full Bangla language support with one click! Rural and first-time users can read plain-language warnings: 'টাকা পাঠানোর আগে প্রাপককে সরাসরি ফোন করে নিশ্চিত হোন।'*
> 
> *The user maintains human oversight: they can cancel to protect their money or verify before continuing."*

---

### **[1:25 - 1:55] The AI Engine Lab & Analyst Portal**
*(Screen recording navigates to `/simulator/` and then `/analyst/`)*

**Speaker:**
> *"Behind the scenes, SafeSend is powered by an ensemble of XGBoost for supervised risk classification, Isolation Forest for unsupervised behavioral anomaly detection, and SHAP for local feature attribution.*
> 
> *In our AI Engine Lab, judges and developers can adjust any parameter—from velocity to device signals—and observe real-time feature attributions.*
> 
> *For Upay operations teams, our Analyst Portal monitors live transactions, highlights high-risk transfers, and features an AI Investigation Assistant that answers the three critical questions: What happened? Why is it risky? And what should Upay do next?"*

---

### **[1:55 - 2:20] Model Performance & Real-Life Impact**
*(Screen recording displays the model evaluation metrics table)*

**Speaker:**
> *"Trained on a synthetic dataset of 10,000 transactions, our XGBoost model achieved 100% precision and recall on the hold-out test set, with zero false negatives on injected fraud patterns.*
> 
> *By combining predictive AI, anomaly detection, and explainable human oversight, Upay SafeSend turns every transaction into a protected moment, preserving user trust and establishing the future of secure digital finance in Bangladesh.*
> 
> *Thank you!"*
