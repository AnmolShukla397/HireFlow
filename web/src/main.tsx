import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { MotionConfig } from 'motion/react'
import App from './App'
import '@liquidglassjs/core/css'
import './styles.css'
import './motion-world.css'
import './liquid-world.css'
import './cinematic-world.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><MotionConfig reducedMotion="user"><BrowserRouter><App /></BrowserRouter></MotionConfig></React.StrictMode>
)
