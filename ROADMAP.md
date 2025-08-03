# FR8 AI Coach Roadmap

## 🎯 Core Vision
**Pipeline:** Video → Gemini → Text → TTS → Voice feedback  
**Mission:** Real-time AI coaching for any physical activity  
**Key Insight:** Each activity = same app with different prompts and form detection rules

## 🏗️ Technical Architecture

### Core Stack
- **Backend:** Python + Gemini API + JSON structured output
- **Frontend:** React Native (cross-platform)
- **Video:** Camera API for video feed, 1fps processing
- **Audio:** WebRTC + TTS for voice feedback
- **Data:** Firebase for user data
- **AI:** Gemini 2.5 Pro with thinking models

### Core Processing Loop
1. **Activity validation** - Wrong activity detection
2. **Form analysis** - Computer vision analysis  
3. **Specific feedback** - Contextual coaching advice
4. **Encouragement** - Positive reinforcement
5. **Next steps** - Progressive improvement

## 📱 User Experience Flow
1. **Activity Selection** - Grid of activities with preview videos
2. **Camera Setup** - Permission + positioning guide  
3. **Live Session** - FaceTime-style with overlay feedback
4. **Voice Coach** - Real-time audio feedback ("Bend your knees more!")

## 🚀 Development Phases

### Phase 1: MVP (3 Activities)
- **Basketball** (proven concept - ✅ completed)
- **Yoga** (huge market, clear form feedback)
- **Guitar** (distinctive, visual feedback)

### Phase 2: Expansion (5-6 Activities)  
- Add dance, cooking, boxing
- Polish UI and user experience
- Basic pose detection for visual overlays

### Phase 3: Platform Features
- User-generated activities (upload custom prompts)
- Memory system (previous session context)
- Strava-Peloton style integration

### Development Timeline
- **Day 1:** Backend pipeline working ✅
- **Day 2:** Basic React Native camera + voice
- **Day 3:** Polish UI

## 💰 Business Model
- **Free Tier:** Upload video analysis (asynchronous)
- **Premium Tier:** Live real-time coaching
- **Scaling:** Max session lengths and video durations by plan

## 🎛️ Hyperparameter Optimization

### Tunable Parameters
- **FPS** - Currently 1fps, will be tunable
- **Coach Style** - Michael Jordan, gentle, motivational, etc.
- **Voice Selection** - Different TTS voices and speeds  
- **Max Response Length** - Word limits for feedback
- **Language** - Any language support
- **Skill Level** - Beginner/intermediate/advanced prompting

### Activity-Specific Settings
Each activity has its own configuration with:
- Custom prompts and form detection rules
- User customization (like Cursor IDE)
- Level progression menus
- Activity-specific feedback templates

## 🛡️ Safety & Validation Features

### Activity Validation
- **Wrong activity detection:** "You're doing yoga, not basketball"
- **No activity detection:** "I don't see any movement"  
- **Technical issues:** "I can't see you clearly" (poor lighting/camera)

### User Experience
- **Encouragement:** "Great form!" / "Keep going!"
- **Progressive feedback:** Start basic, get more detailed
- **Time awareness:** "You've been at this for 5 minutes"

### Technical Constraints  
- **Frame rate limits:** "Processing at 1fps"
- **Confidence levels:** "I'm 80% sure about this feedback"
- **Fallback responses:** "I can't analyze this movement"

## 🎯 Personalization Hooks
- **Skill level detection:** "This looks like beginner form"
- **Progress tracking:** "You've improved since last time"  
- **Goal awareness:** "Remember, you're working on flexibility"
- **Session memory:** Previous recommendations supplied to model for context

## 📊 Future Enhancements
- **Statistics tracking** (optional feature)
- **User memory system** for personalized coaching
- **Advanced pose detection** with visual overlays
- **Multi-language support** 
- **Coach personality customization**
- **Integration with fitness platforms**

## 🔧 Technical Notes & Constraints

### Current Status
- **Working:** Basketball video analysis with Gemini 2.5 Pro
- **Fixed:** MAX_TOKENS issue with thinking models (GitHub issue #782)
- **TTS:** ChatGPT TTS working, Cerebrus TTS issues

### Performance Considerations
- **Processing:** 1fps video analysis (Gemini limitation)
- **Response time:** ~12 seconds per segment analysis
- **Token usage:** ~1-6k thinking tokens per request
- **Prompt constraints:** Keep under 200 words, template-based

### Error Handling
- **API errors:** Gemini 500 errors require retry logic
- **JSON parsing:** Robust error handling for malformed responses
- **Fallback responses:** Graceful degradation when analysis fails

### Development Reminders
- Focus on core coaching loop: validate → analyze → feedback → encourage
- Prompt should be template with placeholders, not a novel
- Activity detection prevents wrong-activity confusion
- Frame rate and hyperparameters will be core differentiators