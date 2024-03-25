# Frontend

The frontend is a VanillaJS app using Vite. Follow Vite's [installation guide](https://vitejs.dev/guide/) to get started.

## Local set-up

1. Install dependencies: `npm install`

2. Create a `.env` file with the following:

```bash
VITE_API_URL=http://127.0.0.1:8000
VITE_KIOSK=false
```

3. `npm run dev` and navigate to the localhost URL shown in the terminal!

## Deployment

The _Parcel ATM_ frontend is hosted on Vercel. Follow their deployment instructions.

Make sure the set the `VITE_API_URL` environment in Vercel to your hosted API URL. If you're getting CORS errors, double-check that you added your frontend URL to the backend's allowable origins in [main.py](../backend/main.py).

You might also get CORS errors fetching the pmtiles. I hosted mine on S3, making sure to set the appropriate CORS headers for the bucket. Follow the [protomaps instructions](https://docs.protomaps.com/pmtiles/cloud-storage#amazon-s3) to set-up your own pmtiles in cloud storage.
