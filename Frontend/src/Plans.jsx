import "./Plans.css";

const plans = [
  {
    name: "Free",
    price: "₹0",
    cadence: "forever",
    highlights: [
      "Chat + threaded history",
      "Basic web search",
      "PDF upload (5 MB)",
      "Light OCR",
      "Voice input (30s)"
    ],
    cta: "Stay Free",
    popular: false,
  },
  {
    name: "Pro",
    price: "₹799",
    cadence: "per month",
    highlights: [
      "Everything in Free, plus:",
      "Stock Research (7-node)",
      "Travel Planner (8-node)",
      "Enhanced OCR + ₹ Guard",
      "Full voice (60s) + themes"
    ],
    cta: "Upgrade to Pro",
    popular: true,
  },
  {
    name: "Max",
    price: "₹1,499",
    cadence: "per month",
    highlights: [
      "Everything in Pro, plus:",
      "Solo Trip Planner (HITL)",
      "AI Stock Advisor",
      "Unlimited PDF/RAG",
      "Priority API + Analytics"
    ],
    cta: "Go Max",
    popular: false,
  },
];

function Plans() {
  return (
    <div className="pageShell plansPage">
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Choose</p>
          <h1>Plans</h1>
          <p className="lede">Pick the Sigma GPT plan that fits your flow. There's always a free tier to start.</p>
        </div>
      </header>
      <div className="planGrid">
        {plans.map((plan, idx) => (
          <div className={`planCard ${plan.popular ? "popular" : ""}`} key={idx}>
            {plan.popular && <div className="flag">Most Popular</div>}
            <div className="planTop">
              <h3>{plan.name}</h3>
              <div className="priceRow">
                <span className="price">{plan.price}</span>
                <span className="cadence">/{plan.cadence}</span>
              </div>
            </div>
            <ul>
              {plan.highlights.map((item, i) => (
                <li key={i}>
                  <i className="fa-solid fa-check"></i>
                  {item}
                </li>
              ))}
            </ul>
            <button className="planCta">{plan.cta}</button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Plans;
