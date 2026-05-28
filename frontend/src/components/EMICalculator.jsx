import { useState, useMemo } from "react";
import { Calculator, IndianRupee } from "lucide-react";

const EMI_LABELS = {
  en: {
    title: "EMI Calculator",
    principal: "Loan Amount (₹)",
    rate: "Interest Rate (%)",
    tenure: "Tenure (Years)",
    calculate: "Calculate EMI",
    monthlyEmi: "Monthly EMI",
    totalAmount: "Total Amount",
    totalInterest: "Total Interest",
    reset: "Reset",
    placeholder: {
      principal: "Enter loan amount",
      rate: "Enter interest rate",
      tenure: "Enter tenure in years"
    }
  },
  hi: {
    title: "EMI कैलकुलेटर",
    principal: "लोन राशि (₹)",
    rate: "ब्याज दर (%)",
    tenure: "अवधि (साल)",
    calculate: "EMI निकालें",
    monthlyEmi: "मासिक EMI",
    totalAmount: "कुल राशि",
    totalInterest: "कुल ब्याज",
    reset: "रीसेट",
    placeholder: {
      principal: "लोन राशि दर्ज करें",
      rate: "ब्याज दर दर्ज करें",
      tenure: "सालों में अवधि दर्ज करें"
    }
  },
  mr: {
    title: "EMI कॅल्क्युलेटर",
    principal: "कर्ज रक्कम (₹)",
    rate: "व्याज दर (%)",
    tenure: "कालावधी (वर्षे)",
    calculate: "EMI काढा",
    monthlyEmi: "मासिक EMI",
    totalAmount: "एकूण रक्कम",
    totalInterest: "एकूण व्याज",
    reset: "रीसेट",
    placeholder: {
      principal: "कर्ज रक्कम प्रविष्ट करा",
      rate: "व्याज दर प्रविष्ट करा",
      tenure: "वर्षांमध्ये कालावधी प्रविष्ट करा"
    }
  }
};

export default function EMICalculator({ language = "en" }) {
  const [principal, setPrincipal] = useState("");
  const [rate, setRate] = useState("");
  const [tenure, setTenure] = useState("");

  const labels = EMI_LABELS[language] || EMI_LABELS.en;

  const emiCalculation = useMemo(() => {
    const p = parseFloat(principal);
    const r = parseFloat(rate) / 100 / 12; // Monthly interest rate
    const n = parseFloat(tenure) * 12; // Total months

    if (!p || !r || !n || p <= 0 || r <= 0 || n <= 0) {
      return null;
    }

    // EMI formula: EMI = P × R × (1+R)^N / ((1+R)^N - 1)
    const emi = (p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    const totalAmount = emi * n;
    const totalInterest = totalAmount - p;

    return {
      monthlyEmi: Math.round(emi),
      totalAmount: Math.round(totalAmount),
      totalInterest: Math.round(totalInterest)
    };
  }, [principal, rate, tenure]);

  const handleReset = () => {
    setPrincipal("");
    setRate("");
    setTenure("");
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="emi-calculator glass-card">
      <div className="calculator-header">
        <Calculator size={20} />
        <h3>{labels.title}</h3>
      </div>

      <div className="calculator-form">
        <div className="form-group">
          <label>{labels.principal}</label>
          <input
            type="number"
            value={principal}
            onChange={(e) => setPrincipal(e.target.value)}
            placeholder={labels.placeholder.principal}
            min="1000"
            max="100000000"
          />
        </div>

        <div className="form-group">
          <label>{labels.rate}</label>
          <input
            type="number"
            value={rate}
            onChange={(e) => setRate(e.target.value)}
            placeholder={labels.placeholder.rate}
            min="0.1"
            max="50"
            step="0.1"
          />
        </div>

        <div className="form-group">
          <label>{labels.tenure}</label>
          <input
            type="number"
            value={tenure}
            onChange={(e) => setTenure(e.target.value)}
            placeholder={labels.placeholder.tenure}
            min="1"
            max="30"
          />
        </div>

        <div className="calculator-actions">
          <button
            className="calc-btn primary"
            onClick={() => {}} // Already calculated via useMemo
            disabled={!principal || !rate || !tenure}
          >
            {labels.calculate}
          </button>
          <button className="calc-btn secondary" onClick={handleReset}>
            {labels.reset}
          </button>
        </div>
      </div>

      {emiCalculation && (
        <div className="calculator-results">
          <div className="result-item">
            <span className="result-label">{labels.monthlyEmi}</span>
            <span className="result-value">{formatCurrency(emiCalculation.monthlyEmi)}</span>
          </div>
          <div className="result-item">
            <span className="result-label">{labels.totalAmount}</span>
            <span className="result-value">{formatCurrency(emiCalculation.totalAmount)}</span>
          </div>
          <div className="result-item">
            <span className="result-label">{labels.totalInterest}</span>
            <span className="result-value">{formatCurrency(emiCalculation.totalInterest)}</span>
          </div>
        </div>
      )}
    </div>
  );
}