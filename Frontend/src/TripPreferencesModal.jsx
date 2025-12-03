import { useState, useEffect } from "react";
import "./TripPreferencesModal.css";

/**
 * 📖 Trip Preferences Modal - Human-in-the-Loop UI
 * =================================================
 * 
 * This modal appears when the Solo Trip Planner hits the INTERRUPT node.
 * User fills in their preferences, and the workflow resumes.
 * 
 * Props:
 * - isOpen: boolean - Show/hide modal
 * - tripInfo: {origin, destination, distance_km, destination_info, transport_options}
 * - onSubmit: (preferences) => void - Called when user submits
 * - onClose: () => void - Called when modal closes
 */

function TripPreferencesModal({ isOpen, tripInfo, onSubmit, onClose }) {
    // Form state
    const [travelMode, setTravelMode] = useState("");
    const [vehicleMake, setVehicleMake] = useState("");
    const [vehicleModel, setVehicleModel] = useState("");
    const [fuelType, setFuelType] = useState("");
    const [evRange, setEvRange] = useState("");
    const [currentCharge, setCurrentCharge] = useState("100");
    const [foodPreference, setFoodPreference] = useState("");
    const [budgetLevel, setBudgetLevel] = useState("");
    const [accommodationType, setAccommodationType] = useState("");
    
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [currentStep, setCurrentStep] = useState(1);
    
    // Reset form when modal opens
    useEffect(() => {
        if (isOpen) {
            setCurrentStep(1);
            setTravelMode("");
            setVehicleMake("");
            setVehicleModel("");
            setFuelType("");
            setEvRange("");
            setCurrentCharge("100");
            setFoodPreference("");
            setBudgetLevel("");
            setAccommodationType("");
        }
    }, [isOpen]);
    
    const handleSubmit = async () => {
        setIsSubmitting(true);
        
        const preferences = {
            travel_mode: travelMode,
            vehicle_make: vehicleMake,
            vehicle_model: vehicleModel,
            fuel_type: fuelType,
            ev_range: evRange ? parseInt(evRange) : null,
            current_charge: currentCharge ? parseInt(currentCharge) : null,
            food_preference: foodPreference,
            budget_level: budgetLevel,
            accommodation_type: accommodationType
        };
        
        await onSubmit(preferences);
        setIsSubmitting(false);
    };
    
    const canProceedStep1 = travelMode !== "";
    const canProceedStep2 = foodPreference !== "" && budgetLevel !== "" && accommodationType !== "";
    const showVehicleDetails = travelMode === "personal_vehicle";
    const showEvDetails = fuelType === "ev";
    
    if (!isOpen) return null;
    
    return (
        <div className="modal-overlay">
            <div className="modal-container">
                {/* Header */}
                <div className="modal-header">
                    <div className="modal-icon">🎒</div>
                    <h2>Personalize Your Solo Trip</h2>
                    <button className="modal-close" onClick={onClose}>×</button>
                </div>
                
                {/* Trip Info Banner */}
                <div className="trip-info-banner">
                    <div className="trip-route">
                        <span className="origin">{tripInfo?.origin || "Origin"}</span>
                        <span className="arrow">→</span>
                        <span className="destination">{tripInfo?.destination || "Destination"}</span>
                    </div>
                    <div className="trip-distance">
                        📏 {tripInfo?.distance_km || "?"} km
                    </div>
                </div>
                
                {/* Progress Steps */}
                <div className="step-progress">
                    <div className={`step ${currentStep >= 1 ? 'active' : ''}`}>
                        <span className="step-number">1</span>
                        <span className="step-label">Travel</span>
                    </div>
                    <div className="step-line"></div>
                    <div className={`step ${currentStep >= 2 ? 'active' : ''}`}>
                        <span className="step-number">2</span>
                        <span className="step-label">Preferences</span>
                    </div>
                </div>
                
                {/* Form Content */}
                <div className="modal-content">
                    {currentStep === 1 && (
                        <div className="form-section">
                            <h3>🚗 How would you like to travel?</h3>
                            
                            <div className="travel-options">
                                {[
                                    { value: "personal_vehicle", icon: "🚙", label: "Personal Vehicle" },
                                    { value: "public_transport", icon: "🚌", label: "Public Transport" },
                                    { value: "taxi", icon: "🚕", label: "Taxi/Cab" },
                                    { value: "flight", icon: "✈️", label: "Flight" }
                                ].map(option => (
                                    <div 
                                        key={option.value}
                                        className={`travel-option ${travelMode === option.value ? 'selected' : ''}`}
                                        onClick={() => setTravelMode(option.value)}
                                    >
                                        <span className="option-icon">{option.icon}</span>
                                        <span className="option-label">{option.label}</span>
                                    </div>
                                ))}
                            </div>
                            
                            {/* Vehicle Details - Only show if personal vehicle */}
                            {showVehicleDetails && (
                                <div className="vehicle-details">
                                    <h4>🚙 Your Vehicle Details</h4>
                                    
                                    <div className="form-row">
                                        <div className="form-group">
                                            <label>Make</label>
                                            <input 
                                                type="text" 
                                                placeholder="e.g., Tata, Mahindra"
                                                value={vehicleMake}
                                                onChange={(e) => setVehicleMake(e.target.value)}
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label>Model</label>
                                            <input 
                                                type="text" 
                                                placeholder="e.g., Nexon, XUV700"
                                                value={vehicleModel}
                                                onChange={(e) => setVehicleModel(e.target.value)}
                                            />
                                        </div>
                                    </div>
                                    
                                    <div className="form-group">
                                        <label>⛽ Fuel Type</label>
                                        <div className="fuel-options">
                                            {["petrol", "diesel", "cng", "ev"].map(fuel => (
                                                <button
                                                    key={fuel}
                                                    className={`fuel-btn ${fuelType === fuel ? 'selected' : ''}`}
                                                    onClick={() => setFuelType(fuel)}
                                                >
                                                    {fuel === "ev" ? "🔋 Electric" : fuel.toUpperCase()}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    
                                    {/* EV Details */}
                                    {showEvDetails && (
                                        <div className="ev-details">
                                            <h4>🔋 EV Details</h4>
                                            <div className="form-row">
                                                <div className="form-group">
                                                    <label>Battery Range (km)</label>
                                                    <input 
                                                        type="number" 
                                                        placeholder="e.g., 350"
                                                        value={evRange}
                                                        onChange={(e) => setEvRange(e.target.value)}
                                                    />
                                                </div>
                                                <div className="form-group">
                                                    <label>Current Charge (%)</label>
                                                    <input 
                                                        type="number" 
                                                        placeholder="e.g., 100"
                                                        value={currentCharge}
                                                        onChange={(e) => setCurrentCharge(e.target.value)}
                                                        max="100"
                                                    />
                                                </div>
                                            </div>
                                            <p className="ev-note">
                                                💡 We'll plan charging stops based on your vehicle's range!
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                    
                    {currentStep === 2 && (
                        <div className="form-section">
                            <h3>🎯 Your Preferences</h3>
                            
                            {/* Food Preference */}
                            <div className="form-group">
                                <label>🍽️ Food Preference</label>
                                <div className="preference-options">
                                    {[
                                        { value: "veg", label: "🥬 Vegetarian" },
                                        { value: "non_veg", label: "🍗 Non-Veg" },
                                        { value: "vegan", label: "🌱 Vegan" },
                                        { value: "eggetarian", label: "🥚 Eggetarian" }
                                    ].map(option => (
                                        <button
                                            key={option.value}
                                            className={`pref-btn ${foodPreference === option.value ? 'selected' : ''}`}
                                            onClick={() => setFoodPreference(option.value)}
                                        >
                                            {option.label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            
                            {/* Budget Level */}
                            <div className="form-group">
                                <label>💰 Budget Level</label>
                                <div className="preference-options">
                                    {[
                                        { value: "budget", label: "💵 Budget", desc: "₹500-1500/day" },
                                        { value: "mid_range", label: "💳 Mid-Range", desc: "₹1500-4000/day" },
                                        { value: "premium", label: "💎 Premium", desc: "₹4000+/day" }
                                    ].map(option => (
                                        <button
                                            key={option.value}
                                            className={`pref-btn budget-btn ${budgetLevel === option.value ? 'selected' : ''}`}
                                            onClick={() => setBudgetLevel(option.value)}
                                        >
                                            <span>{option.label}</span>
                                            <small>{option.desc}</small>
                                        </button>
                                    ))}
                                </div>
                            </div>
                            
                            {/* Accommodation */}
                            <div className="form-group">
                                <label>🏨 Accommodation Preference</label>
                                <div className="preference-options">
                                    {[
                                        { value: "hotel", label: "🏨 Hotel" },
                                        { value: "hostel", label: "🛏️ Hostel" },
                                        { value: "airbnb", label: "🏠 Airbnb" },
                                        { value: "camping", label: "⛺ Camping" },
                                        { value: "none", label: "🚗 No Stay" }
                                    ].map(option => (
                                        <button
                                            key={option.value}
                                            className={`pref-btn ${accommodationType === option.value ? 'selected' : ''}`}
                                            onClick={() => setAccommodationType(option.value)}
                                        >
                                            {option.label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
                
                {/* Footer with buttons */}
                <div className="modal-footer">
                    {currentStep === 1 ? (
                        <button 
                            className="btn-primary"
                            disabled={!canProceedStep1}
                            onClick={() => setCurrentStep(2)}
                        >
                            Next: Preferences →
                        </button>
                    ) : (
                        <>
                            <button 
                                className="btn-secondary"
                                onClick={() => setCurrentStep(1)}
                            >
                                ← Back
                            </button>
                            <button 
                                className="btn-primary"
                                disabled={!canProceedStep2 || isSubmitting}
                                onClick={handleSubmit}
                            >
                                {isSubmitting ? (
                                    <>
                                        <i className="fa-solid fa-spinner fa-spin"></i> Planning...
                                    </>
                                ) : (
                                    <>
                                        🚀 Create My Solo Trip
                                    </>
                                )}
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

export default TripPreferencesModal;

