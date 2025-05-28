# ShortsTurbo 🚀

**AI-Powered Short Video Generator for YouTube & TikTok Monetization**

ShortsTurbo is an open-source, AI-powered software that automatically generates engaging short videos for YouTube Shorts and TikTok. Simply provide a script, and the system will automatically generate video materials, subtitles, background music, and synthesize everything into high-definition short videos ready for monetization.

## ✨ Features

### 🎬 **Automated Video Generation**
- **Script-to-Video**: Transform text scripts into complete short videos
- **AI Material Sourcing**: Automatically fetch relevant video clips from Pexels, Pixabay, or use local files
- **Smart Video Editing**: Intelligent clip selection, transitions, and concatenation
- **Multiple Aspect Ratios**: Support for 9:16 (Portrait) and 16:9 (Landscape) formats

### 🎙️ **Advanced Text-to-Speech**
- **Multiple TTS Providers**: Azure TTS V1/V2, SiliconFlow TTS
- **Natural Voices**: Wide selection of high-quality, natural-sounding voices
- **Multi-language Support**: Generate content in multiple languages
- **Voice Customization**: Fine-tune speech parameters for optimal engagement

### 📝 **Intelligent Subtitle Generation**
- **Auto-Generated Subtitles**: AI-powered subtitle creation with perfect timing
- **Custom Fonts**: Support for various font styles and formatting
- **Subtitle Positioning**: Optimized placement for maximum readability
- **Multi-language Subtitles**: Generate subtitles in different languages

### 🎵 **Background Music Integration**
- **BGM Library**: Built-in background music management
- **Custom Music Upload**: Support for MP3 file uploads
- **Audio Mixing**: Automatic audio level balancing
- **Royalty-Free Options**: Avoid copyright issues with curated music

### 🔄 **Batch Processing**
- **Multiple Scripts**: Process multiple video scripts simultaneously
- **Bulk Generation**: Generate dozens of videos with consistent settings
- **Keyword Extraction**: Automatic keyword detection from filenames and content
- **Efficient Workflow**: Streamlined process for content creators

### 🌐 **Dual Interface**
- **Web UI (Streamlit)**: User-friendly interface for interactive video creation
- **REST API**: Programmatic access for automation and integration
- **Real-time Monitoring**: Track video generation progress
- **Task Management**: Queue and manage multiple video generation tasks

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- FFmpeg
- Docker (optional)

### Installation

#### Option 1: Docker (Recommended)
```bash
git clone https://github.com/your-username/ShortsTurbo.git
cd ShortsTurbo
docker-compose up -d
```

#### Option 2: Local Installation
```bash
git clone https://github.com/your-username/ShortsTurbo.git
cd ShortsTurbo
pip install -r requirements.txt
```

### Usage

#### Web Interface
```bash
# Start the Streamlit web interface
streamlit run webui/Main.py
```
Access the web interface at `http://localhost:8501`

#### API Server
```bash
# Start the FastAPI server
python main.py
```
API documentation available at `http://localhost:8080/docs`

## 💰 Monetization Strategies

### YouTube Shorts
- **Faceless Content**: Create engaging content without showing your face
- **Trending Topics**: Generate videos on viral subjects and current events
- **Educational Content**: Create how-to guides, facts, and tutorials
- **Entertainment**: Produce funny, inspiring, or thought-provoking content

### TikTok
- **Viral Formats**: Leverage popular TikTok video formats and trends
- **Quick Facts**: Generate bite-sized educational content
- **Motivational Content**: Create inspiring and uplifting videos
- **News & Updates**: Produce timely content on current events

### Content Ideas
- **Daily Facts**: Generate educational content with interesting facts
- **Motivational Quotes**: Create inspiring quote videos with visuals
- **News Summaries**: Produce quick news update videos
- **How-To Guides**: Generate instructional content on various topics
- **Product Reviews**: Create review videos using product information

## 🛠️ Technical Stack

- **Backend**: FastAPI, Python
- **Frontend**: Streamlit
- **Video Processing**: MoviePy, FFmpeg
- **AI Services**: Google Generative AI, Azure Cognitive Services
- **Task Management**: Redis (optional), In-memory queue
- **Containerization**: Docker, Docker Compose

## 📁 Project Structure

```
ShortsTurbo/
├── app/                    # Core application
│   ├── controllers/        # API endpoints
│   ├── services/          # Business logic
│   ├── models/            # Data models
│   └── utils/             # Utility functions
├── webui/                 # Streamlit web interface
├── resource/              # Fonts, assets
├── storage/               # Generated content
├── docker-compose.yml     # Docker configuration
└── requirements.txt       # Python dependencies
```

## 🔧 API Endpoints

### Video Generation
- `POST /videos` - Generate complete short videos
- `POST /subtitle` - Generate subtitles only
- `POST /audio` - Generate audio only

### Task Management
- `GET /tasks` - List all tasks
- `GET /tasks/{task_id}` - Get task status
- `DELETE /tasks/{task_id}` - Delete task

### Media Management
- `GET /musics` - List background music files
- `POST /musics` - Upload background music
- `GET /stream/{file_path}` - Stream video files
- `GET /download/{file_path}` - Download generated videos

## 🎯 Use Cases

### Content Creators
- **Scale Content Production**: Generate multiple videos daily
- **Consistent Quality**: Maintain professional video standards
- **Time Efficiency**: Reduce video creation time from hours to minutes
- **Cost Effective**: Eliminate need for expensive video editing software

### Businesses
- **Marketing Content**: Create promotional videos for products/services
- **Educational Material**: Develop training and instructional content
- **Social Media Presence**: Maintain active social media channels
- **Brand Awareness**: Generate content that showcases expertise

### Agencies
- **Client Content**: Produce content for multiple clients efficiently
- **Scalable Solutions**: Handle large volume content requests
- **Automated Workflows**: Integrate with existing content pipelines
- **White-label Solutions**: Customize for agency branding

## 🔒 Privacy & Security

- **Local Processing**: All video generation happens on your infrastructure
- **No Data Sharing**: Your scripts and content remain private
- **API Key Security**: Secure handling of third-party API credentials
- **Content Ownership**: You retain full ownership of generated content

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [Wiki](https://github.com/your-username/ShortsTurbo/wiki)
- **Issues**: [GitHub Issues](https://github.com/your-username/ShortsTurbo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/ShortsTurbo/discussions)

## 🌟 Star History

If you find ShortsTurbo useful, please consider giving it a star! ⭐

## 🚀 Roadmap

- [ ] Additional TTS providers
- [ ] More video sources and stock footage
- [ ] Advanced video effects and transitions
- [ ] AI-powered script generation
- [ ] Social media scheduling integration
- [ ] Analytics and performance tracking
- [ ] Mobile app development

---

**Start generating profitable short videos today with ShortsTurbo!** 🎬💰