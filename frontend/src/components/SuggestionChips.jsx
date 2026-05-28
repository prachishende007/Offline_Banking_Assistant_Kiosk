const DEFAULT_SUGGESTIONS = {
  en: ["Check account balance", "Last 5 transactions", "My account details", "Loan interest info", "Calculate EMI"],
  hi: ["मेरा बैलेंस बताओ", "पिछले पांच लेनदेन", "मेरा खाता विवरण", "लोन ब्याज जानकारी", "EMI कैलकुलेट करें"],
  mr: ["माझी शिल्लक सांगा", "माझे शेवटचे पाच व्यवहार", "माझे खाते तपशील", "कर्ज व्याज माहिती", "EMI कॅल्क्युलेट करा"],
};

export default function SuggestionChips({ language = "en", onPick, suggestions }) {
  const list = suggestions || DEFAULT_SUGGESTIONS[language] || DEFAULT_SUGGESTIONS.en;
  return (
    <div className="chips-wrap">
      {list.map((text) => (
        <button key={text} className="chip" onClick={() => onPick(text)}>
          {text}
        </button>
      ))}
    </div>
  );
}
