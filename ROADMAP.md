# FR8 AI Coach Roadmap

> **Note:** FPS and many other parameters will be tunable - this will be my hyperparameter tuning

As a hackathon veteran, here's your roadmap:

## Phase 1: MVP Scope (Weekend Hackathon Style)
**Start with 3 activities max:**
- Basketball (proven concept)
- Yoga (huge market, clear form feedback)
- Guitar (distinctive, visual feedback)

## Phase 2: Technical Architecture
**Core Stack:**
- React Native (cross-platform)
- Camera API for video feed
- Gemini API for real-time analysis
- WebRTC for voice feedback
- Firebase for user data

## Phase 3: User Experience Flow
1. **Activity Selection** - Grid of 3 activities with preview videos
2. **Camera Setup** - Permission + positioning guide
3. **Live Session** - FaceTime-style with overlay feedback
4. **Voice Coach** - "Bend your knees more" / "Great form!"

## Phase 4: Growth Strategy
- **Phase 1:** 3 activities, manual prompt tuning
- **Phase 2:** Add 2-3 more (dance, cooking, boxing)
- **Phase 3:** User-generated activities (upload custom prompts)

**Start coding now.** The vision is clear - build the basketball mode first, then add yoga/guitar. Each activity is essentially the same app with different prompts and form detection rules.

## Key Features

### Pipeline
**Your pipeline:** Video → Gemini → Text → TTS → Voice  
**Add:** Basic pose detection for visual overlays

### Development Timeline
- Day 1: Backend pipeline working
- Day 2: Basic React Native camera + voice
- Day 3: Polish UI

### Pricing Model
- **Two modes:** live (premium) upload video (FREE)
- Language will be any language

### Customization
Each board will have its own settings, but then the user can prompt just like Cursor or any other app where you have the preset stuff in the backend and then the user can customize it. And then there'll be like level menus such as boards, cooking, instruments, and then within those it'll be like a Strava-Peloton integration.

The prompt should also say, if the user is not doing at all what is chosen, then say this is the wrong activity.

Eventually will have memory on the user in the roadmap.

## Feedback Categories

### Safety & Validation
- Wrong activity detection - "You're doing yoga, not basketball"
- No activity happening - "I don't see any movement"
- Poor lighting/camera - "I can't see you clearly"

### User Experience
- Encouragement - "Great form!" / "Keep going!"
- Progressive feedback - Start basic, get more detailed
- Time awareness - "You've been at this for 5 minutes"

### Technical Constraints
- Frame rate limits - "Processing at 1fps"
- Confidence levels - "I'm 80% sure about this feedback"
- Fallback responses - "I can't analyze this movement"

### Personalization Hooks
- Skill level detection - "This looks like beginner form"
- Progress tracking - "You've improved since last time"
- Goal awareness - "Remember, you're working on flexibility"

## Core Structure
Apply to temp_speech...
1. Activity validation
2. Form analysis
3. Specific feedback
4. Encouragement
5. Next steps

Keep it under 200 words. The prompt should be a template with placeholders for activity-specific details, not a novel.
Focus on the core coaching loop: validate → analyze → feedback → encourage.

## Future Features
- Statistics will be optional in the future
- I will eventually supply the previous recommendations in the prompt to the model so that it has context on what happened before
- You can choose the voice is another optimization we will do and the speed of the voice - this is going to be so fucking good
- I will also need to have max session lengths and video durations. Scale if you're on the premium plan
- Coach style will be another hyperparameter, this is going to be so good, and bitter-lesson pilled

## Technical Notes
- Gemini and Cerebrus TTS are not working
- I'll have to learn to start dealing with these errors because they seem inevitable: `{'code': 500, 'message': 'An internal error has occurred. Please retry or report in https://developers.generativeai.google/guide/troubleshooting', 'status': 'INTERNAL'}}`
- Remember that the guy used 1 fps, so I need to play with that