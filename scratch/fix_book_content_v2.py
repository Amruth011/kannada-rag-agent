# scratch/fix_book_content_v2.py
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KANNADA_DIR = os.path.join(BASE_DIR, "data", "normalized_text")
ENGLISH_DIR = os.path.join(BASE_DIR, "data", "english_translated")

# Corrected content dictionary
KANNADA_FIXES = {
    2: """ಹೇಳಿ ಹೋಗು ಕಾರಣ (ಕಾದಂಬರಿ)
ರವಿ ಬೆಳಗೆರೆ

ಭವನ ಪ್ರಕಾಶನ
#೨, ೮೦ ಅಡಿ ರಸ್ತೆ, ಬನಶಂಕರಿ ೨ನೇ ಹಂತ, ಪದ್ಮನಾಭನಗರ, ಬೆಂಗಳೂರು - ೫೬೦ ೦೭೦
ಇ-ಮೇಲ್: bhavanaprakashana@gmail.com
ವೆಬ್‌ಸೈಟ್: www.ravibelagere.com
ದೂರವಾಣಿ: 94480 51726""",

    3: """ಹೇಳಿ ಹೋಗು ಕಾರಣ (ಕಾದಂಬರಿ)
ರವಿ ಬೆಳಗೆರೆ
ಪುಟಗಳು: ೩೩೯
ಬೆಲೆ: ೩೫೦ ರೂ.
ಪ್ರತಿಗಳು: ೩೦೦೦
ಮುದ್ರಣ: ಶ್ರೀ ಗಣೇಶ ಮುದ್ರಣಾಲಯ ಪ್ರ.ಲಿ, ಬೆಂಗಳೂರು.

ಮುದ್ರಣ ಇತಿಹಾಸ:
ಮೊದಲ ಮುದ್ರಣ: ಸೆಪ್ಟೆಂಬರ್ ೨೦೦೩
ಎರಡನೇ ಮುದ್ರಣ: ನವೆಂಬರ್ ೨೦೦೮
ಮೂರನೇ ಮುದ್ರಣ: ಏಪ್ರಿಲ್ ೨೦೦೯
ನಾಲ್ಕನೇ ಮುದ್ರಣ: ಡಿಸೆಂಬರ್ ೨೦೦೯
ಐದನೇ ಮುದ್ರಣ: ಅಕ್ಟೋಬರ್ ೨೦೧೦
ಆರನೇ ಮುದ್ರಣ: ಡಿಸೆಂಬರ್ ೨೦೧೧
ಏಳನೇ ಮುದ್ರಣ: ಏಪ್ರಿಲ್ ೨೦೧೨
ಎಂಟನೇ ಮುದ್ರಣ: ಫೆಬ್ರವರಿ ೨೦೧೩
ಒಂಬತ್ತನೇ ಮುದ್ರಣ: ಜೂನ್ ೨೦೧೪
ಹತ್ತನೇ ಮುದ್ರಣ: ಜನವರಿ ೨೦೧೫
ಹನ್ನೊಂದನೇ ಮುದ್ರಣ: ಜನವರಿ ೨೦೧೬
ಹನ್ನೆರಡನೇ ಮುದ್ರಣ: ಆಗಸ್ಟ್ ೨೦೧೬
ಹದಿಮೂರನೇ ಮುದ್ರಣ: ಜೂನ್ ೨೦೧೭
ಹದಿನಾಲ್ಕನೇ ಮುದ್ರಣ: ಆಗಸ್ಟ್ ೨೦೧೮
ಹದಿನೈದನೇ ಮುದ್ರಣ: ಜುಲೈ ೨೦೧೯
ಹದಿನಾರನೇ ಮುದ್ರಣ: ಡಿಸೆಂಬರ್ ೨೦೧೯
ಹದಿನೇಳನೇ ಮುದ್ರಣ: ಆಗಸ್ಟ್ ೨೦设置
ಹದಿನೆಂಟನೇ ಮುದ್ರಣ: ಜನವರಿ ೨೦೨೧
ಹತ್ತೊಂಬತ್ತನೇ ಮುದ್ರಣ: ಆಗಸ್ಟ್ ೨೦೨೧
ಇಪ್ಪತ್ತನೇ ಮುದ್ರಣ: ಜನವರಿ ೨೦೨೨
ಇಪ್ಪತ್ತೊಂದನೇ ಮುದ್ರಣ: ಜುಲೈ ೨೦೨೨
ಇಪ್ಪತ್ತೆರಡನೇ ಮುದ್ರಣ: ಜನವರಿ ೨೦೨೩
ಇಪ್ಪತ್ಮೂರನೇ ಮುದ್ರಣ: ಜೂನ್ ೨೦೨೩
ಇಪ್ಪತ್ನಾಲ್ಕನೇ ಮುದ್ರಣ: ಆಗಸ್ಟ್ ೨೦೨೩
ಇಪ್ಪತ್ತೈದನೇ ಮುದ್ರಣ: ಡಿಸೆಂಬರ್ ೨೦೨೩
ಇಪ್ಪತ್ತಾರನೇ ಮುದ್ರಣ: ಮಾರ್ಚ್ ೨೦೨೪
ಇಪ್ಪತ್ತೇಳನೇ ಮುದ್ರಣ: ಜೂನ್ ೨೦೨೪
ಇಪ್ಪತ್ತೆಂಟನೇ ಮುದ್ರಣ: ಆಗಸ್ಟ್ ೨೦೨೪
ಇಪ್ಪತ್ತೊಂಬತ್ತನೇ ಮುದ್ರಣ: ನವೆಂಬರ್ ೨೦೨೪
ಮೂವತ್ತನೇ ಮುದ್ರಣ: ಜನವರಿ ೨೦೨೫
ಮೂವತ್ತೊಂದನೇ ಮುದ್ರಣ: ಏಪ್ರಿಲ್ ೨೦೨೫""",

    11: """ಸ್ವಲ್ಪ ಹೊತ್ತು ಸುಮ್ಮನೆ ಕುಳಿತಿದ್ದಳು. "ಹಿಮವಂತ್!" ಅವಳು ಕಣ್ಣುಗಳಲ್ಲಿ ಒಂದು ರೀತಿಯ ಧೃತಿಗೆಟ್ಟು ಕರೆದಳು. ಆ ರಾತ್ರಿ ಕೂಡ ನರಕದಂತಿತ್ತು. ಪಟ್ಟಣದ ದೀಪಗಳು ಆರಿಹೋಗಿದ್ದವು. ತಲೆ ತಗ್ಗಿಸಿದವಳನ್ನೇ ಇವನೆಲ್ಲೋ ಲೇಪಿಸಿ ಹಚ್ಚಿರಬೇಕು ಭಗವಂತ! ಅವಳು ಧರಿಸಿದ್ದ ಉಡುಪು ಅವಳಿಗೆ ಹೊಸ ರೂಪ ತಿದ್ದಿರಬೇಕು ಭಗವಂತ! ಲಜ್ಜೆ ಕಲಿಸಿದುದು ಸಾತ್ವಿಕ ಬೆರಗಿನ ನಗು. ಅವಳ ಕಣ್ಣುಗಳಲ್ಲಿ ಒಂದು ರೀತಿಯ ಕಾನ್ಫಿಡೆನ್ಸ್ ಸುಳಿದಾಡುತ್ತಿತ್ತು. ಬೆಳೆದ ಹುಡುಗಿಯರಲ್ಲಿ ಈ ಅಮಾಯಕತೆ ಸತ್ತು ಹೋಗಿರುತ್ತದೆ. ಬುದ್ಧಿ ಬೆಳೆಯದ ಸುಂದರಿಯರ ಮುಖದಲ್ಲಿ ತೇಲುವುದು ಅಮಾಯಕತೆಯಲ್ಲ; ದುಷ್ಟತನದ ಕಾನ್ಫಿಡೆನ್ಸ್ ಮತ್ತು ಅಮಾಯಕತೆಗಳೆರಡೂ ಬೆರೆತ ಮುಖದಲ್ಲಿ ಮಾತ್ರ ಲಲಿತವೆನಿಸುತ್ತದೆ. ಬಹುಶಃ ಅದನ್ನೇ ಹೇಳಿದ್ದು. ಹಾಗೆ ಅಂದುಕೊಳ್ಳುತ್ತಿರುವಾಗಲೇ ಅವಳ ಸಮ್ಮತಿ ಸಿಕ್ಕಿಹೋಗುತ್ತದೆ.
ಹಾಗೆ ಚನ್ನರಾಯಪಟ್ಟಣದಿಂದ ಹೊರಟು ಆ ರಾತ್ರಿಯಲ್ಲಿ ಇಬ್ಬರು ಅಸ್ಪಷ್ಟ ನೆರಳುಗಳು ನಡೆದು ಬಂದು ಶಿವಮೂರ್ತಿ ಸರ್ಕಲ್‌ನ ಸಮೀಪದ ಮುಂಡಿ ಮರ್ಚೆಂಟ್ ಶಾಂತಪ್ಪನವರ ಮನೆಯ ಹಿತ್ತಿಲಲ್ಲಿದ್ದ ಪುಟ್ಟ ಕೋಣೆಯೊಳಕ್ಕೆ ದಾಖಲಾದುದನ್ನು ಯಾರೂ ಗಮನಿಸಿರಲಿಲ್ಲ, ಒಬ್ಬ ರಸೂಲ್ ಜಮಾದಾರನ ಹೊರತಾಗಿ. ಅವನು ಸದ್ದಿಲ್ಲದೆ ನಡೆದು ಬಂದು ಕೋಣೆಯ ಬಾಗಿಲಿಗೆ ನಿಂತು ಅವರಿಬ್ಬರೂ ಕೋಣೆ ತಲುಪಿದ್ದನ್ನು ಖಾತರಿ ಮಾಡಿಕೊಂಡೇ ಹಿಂತಿರುಗಿದ್ದ.
ಆ ನೆರಳುಗಳಿಗೆ ಇಡೀ ಜಗತ್ತಿನಲ್ಲಿ ಮತ್ತೊಂದು ಆಸರೆಯಿರಲಿಲ್ಲ. ಒಂದು ನೆರಳು ನಿಸ್ಸಹಾಯಕತೆಯಿಂದ ಒದ್ದಾಡುತ್ತಿತ್ತು, ಇನ್ನೊಂದು ನೆರಳು ಸಮ್ಮತಿಯಿಂದ ಕೈ ಹಿಡಿದಿತ್ತು.
"ನಿಜಕ್ಕೂ ನನಗೊಂದು ಬದುಕು ಕೊಡುತ್ತೀಯಾ ಹಿಮವಂತ್?" ಮೊದಲ ಭೇಟಿಯ ದಿನಗಳಲ್ಲಿ ಹಾಗಂತ ಕೇಳಿದ್ದಳು ಪ್ರಾರ್ಥನಾ.
"ಗೊತ್ತಿಲ್ಲ. ಆದರೆ ಬದುಕು ನನಗೆ ಕೊಟ್ಟಿದ್ದನ್ನೆಲ್ಲ ನಿರ್ವಂಚನೆಯಿಂದ ನಿನಗೆ ಕೊಟ್ಟುಬಿಡಬಲ್ಲೆ. ಅದಕ್ಕೆ ಬದಲಾಗಿ ನೀನು ನನಗೆ ಏನು ಕೊಡ್ತೀಯಾ ಅಂತ ನಾನು ಕೇಳುವುದಿಲ್ಲ. ಏಕೆಂದರೆ ಬದುಕು ಕೊಡುವಂಥದ್ದೂ ಅಲ್ಲ, ಇಸಿದು ಕೊಳ್ಳುವಂಥದ್ದೂ ಅಲ್ಲ. ಅದು ಕಟ್ಟಿಕೊಳ್ಳುವಂಥದ್ದು. ನಿನ್ನ ಮನೆಯಿಂದ ಎದ್ದು ಬಂದ ನರಕ ಅಲ್ಲಿಗೆ ಮುಗಿಯಲಿ. ಚನ್ನರಾಯಪಟ್ಟಣದ ಬಸ್ ಸ್ಟ್ಯಾಂಡಿನಲ್ಲಿ ನಿನಗೋಸ್ಕರ ಕಾದಿರುತ್ತೇನೆ. ಶಿವಮೊಗ್ಗ ತಲುಪಲು ಸಾವಿರ ಬಸ್ಸುಗಳಿರಬಹುದು, ಹತ್ತು ದಾರಿಗಳಿರಬಹುದು ಆದರೆ ನೆನಪಿರಲಿ: ನಾವು ನಡೆದೇ ಹೋಗಬೇಕು. ರಾಜಬೀದಿಯಲ್ಲೇ ನಡೆಯಬೇಕು. ಚನ್ನರಾಯಪಟ್ಟಣದಿಂದ ಶಿವಮೊಗ್ಗ ತಲುಪುವ ತನಕ ಯಾವ ಕನಸು ಬೇಕಾದರೂ ಕಾಣು ಪ್ರಾರ್ಥನಾ. ಶಿವಮೊಗ್ಗದ ನನ್ನ ಮನೆಯ ಹೊಸ್ತಿಲೊಳಕ್ಕೆ ಕಾಲಿಟ್ಟ ಕ್ಷಣದಿಂದ...""",

    338: """ಹೇಳಿ ಹೋಗು ಕಾರಣ / ೩೩೮
ದೇಬುವಿನ ತಂದೆ ತಾಯಿಯರಿಗೆ ಕಾಲು ಮುಟ್ಟಿ ನಮಸ್ಕರಿಸಿದಳು. ಯಾಂತ್ರಿಕವಾಗಿ ತಲೆ ಸವರಿ, ಅಕ್ಕರೆಯಿಂದ ಬೆನ್ನು ತಟ್ಟಿದ ದೇಬುವಿನ ತಂದೆಯನ್ನು ನೋಡಿ ಅವಳಿಗೆ ಬಂದ ದುಃಖ ತಡೆಯಲಾಗದೆ ಬಿಕ್ಕಿ ಬಿಕ್ಕಿ ಅತ್ತುಬಿಟ್ಟಳು. ಆದರೆ ಒತ್ತರಿಸಿ ಬಂದ ದುಃಖವನ್ನು ಹತ್ತಿಕ್ಕಿಕೊಂಡು ಸೋಫಾದ ಮೇಲೆ ದಿಗ್ಮೂಢನಾದವನಂತೆ ಕುಳಿತಿದ್ದ ದೇಬುವಿನ ಬಳಿಗೆ ಬಂದಾಗ, ಅವಳ ಮನಸ್ಸು ಸರೋವರದಂತೆ ನಿಶ್ಚಲವಾಗಿ ಎಲ್ಲ ಉದ್ವೇಗಗಳ ಜ್ವಾಲಾಮುಖಿ ಇದ್ದಕ್ಕಿದ್ದಂತೆ ಬರಿದಾಗಿ ಹೋಯಿತು. "Good bye Debu..." ಅಂದವಳೇ ಅವನ ಹಣೆಗೊಂದು ಹೂಮುತ್ತನ್ನಿಟ್ಟು, ಇನ್ನು ಅಲ್ಲಿ ನಿಲ್ಲಲಾಗದೆಂಬಂತೆ ಪೋರ್ಟಿಕೋದಡೆಗೆ ನಡೆಯತೊಡಗಿದಳು.
ಅವಳು ವರಾಂಡ ದಾಟುತ್ತಿದ್ದಾಗ ದೇಬ್ ಬಾಬು ಏನನ್ನೋ ಹೇಳಲು ದನಿ ಹೊರಡಿಸಿದ. ಇನ್ನು ಒಂದೇ ಒಂದು ಸಲ ಅವನ ಅಸ್ಪಷ್ಟವಾದ ದನಿಯನ್ನು ಕೇಳಿಸಿಕೊಂಡುಬಿಟ್ಟರೆ ತನ್ನ ಎದೆಯೇ ಒಡೆದು ಹೋದೀತೆನಿಸಿ, ಸರಸರನೆ ವರಾಂಡದಲ್ಲಿ ನಿಂತಿದ್ದ ಊರ್ಮಿಳೆಯೆಡೆಗೆ ಹೆಜ್ಜೆ ಹಾಕಿ, "ಹೊರಡು ದೀದಿ, let's go!" ಅಂದಳು ಪ್ರಾರ್ಥನಾ.
"ಇಲ್ಲ, he wants you alone in the car. ಜೊತೆಗೆ ನಾವ್ಯಾರೂ ಬರಕೂಡದು ಅಂತ ಹೇಳಿಬಿಟ್ಟಿದ್ದಾನೆ ಹಿಮು. ನೀನು ಹೊರಡು, ನಾವು ಬೇರೆ ಕಾರಿನಲ್ಲಿ ಬರ್ತೇವೆ. ನಾನು, ಜಮಾದಾರ ಮತ್ತು ದೇಬು!" ಅಂದುಬಿಟ್ಟಳು ಊರ್ಮಿಳಾ.
ಪ್ರಾರ್ಥನಾಳ ಕಣ್ಣಲ್ಲಿ ಚಂಡಮಾರುತ. ದೇಬು ಎಲ್ಲಿಗೆ ಬರ್ತಾನೆ? ಯಾಕೆ ಬರ್ತಾನೆ? ಭಗವಂತಾ, ಇನ್ನೂ ಏನೇನು ಆಗಬೇಕಿದೆ? ಹಾಗಂತ ಕೇಳಿಯೇಬಿಟ್ಟಳು ಪ್ರಾರ್ಥನಾ.
"ದೇಬು ಪೂರ್ತಿಯಾಗಿ ಚೇತರಿಸಿಕೊಳ್ಳೋದಕ್ಕೆ ವಾರಗಳೇ ಬೇಕು. ಅವನ ಜೊತೆಗೆ ಒಬ್ಬ ಡಾಕ್ಟರ್ ಸದಾ ಇರಬೇಕು. ಡಾಕ್ಟರಲ್ಲದಿದ್ದರೆ atleast an attendant. ನೀನು ಅನಿವಾರ್ಯವಾಗಿ ಹೊರಟಿದ್ದೀಯ. ದೇಬುವಿನ ಅಪ್ಪ ಅಮ್ಮ ಈ ಸ್ಥಿತಿಯಲ್ಲಿ ಅವನನ್ನು ನೋಡಿಕೊಳ್ಳಲಾರರು. ಶಿವಮೊಗ್ಗದಲ್ಲಿ ನನ್ನ ಪರಿಚಯವಿರೋ ಡಾಕ್ಟರೊಬ್ಬರ ನರ್ಸಿಂಗ್ ಹೋಮ್ ಇದೆ. ಅವನನ್ನು ಈ ಸ್ಥಿತಿಯಲ್ಲಿ ದಾವಣಗೆರೆ ಕಾಲೇಜಿಗೆ ಕರ್ಕೊಂಡು ಹೋಗೋ ಮನಸಿಲ್ಲ ನನಗೆ. ಅಷ್ಟು ಸ್ಫುರದ್ರೂಪಿಯಾಗಿದ್ದ ದೇಬೂನ ಜನ ಈ ಸ್ಥಿತಿಯಲ್ಲಿ ನೋಡಬಾರದು. ನಂಗಿದೆಲ್ಲ ಒಂಥರಾ ಅಭ್ಯಾಸವಾಗಿಬಿಟ್ಟ ಹಾಗಿದೆ. ನೀನು ಯಾರನ್ನೋ ಬಿಟ್ಟು ಹೋಗ್ತೀಯಾ, ನಾನು ಅವರನ್ನು attend ಮಾಡೋ ನಿರ್ಣಯಕ್ಕೆ ಬಂದುಬಿಡ್ತೀನಿ. ಹೀಗ್ಯಾಕೆ ಹೋಗಿಬಿಡ್ತೀಯಾ? ಬದುಕು ಪದೇಪದೆ ನಮ್ಮಿಬ್ಬರನ್ನೂ ಇಂಥ crossroads ಗೆ ತಂದು ನಿಲ್ಲಿಸುತ್ತೋ ಅರ್ಥವಾಗ್ತಿಲ್ಲ. ನೀನು ಹೊರಡು, ದೇಬೂ ಬಗ್ಗೆ ಅವರ ತಂದೆ ತಾಯಿಗೆ ಕನ್ವಿನ್ಸ್ ಮಾಡಿ ಅವನನ್ನು ಕರ್ಕೊಂಡು ನಾನು ಟ್ಯಾಕ್ಸಿಯಲ್ಲಿ ಶಿವಮೊಗ್ಗಕ್ಕೆ ಬರ್ತೀನಿ, I will try to meet you..." ನೊಂದ ದನಿಯಲ್ಲಿ ಊರ್ಮಿಳಾ ಮಾತನಾಡಿದಳು. ಪ್ರಾರ್ಥನಾಳ ಪ್ರಶ್ನೆ, ಕುತೂಹಲ, ಆತಂಕಗಳೆಲ್ಲ ಒಂದೇ ಹೊಡೆತಕ್ಕೆ ಸತ್ತು ಹಿಮವಂತನೊಂದಿಗೆ ಶಿವಮೊಗ್ಗದ ಅದೇ ಪರಿಚಿತ ಬದುಕಿಗೆ ಹೋದಂತಾದವು.""",

    341: """ಹೇಳಿ ಹೋಗು ಕಾರಣ / ೩೪೧
ಹೋಗುವ ಮುನ್ನ ಅವನನ್ನು ನೋಡಿಬರಲು ತಾನಾಗಿಯೇ ಒಪ್ಪಿದ್ದೇಕೆ? ಕೊನೆಯ ಬಾರಿಗೆ ಅವನನ್ನು ಹಾಗೆ ಕಂಡಮೇಲೆ ತಾನೀಗ ಬದುಕಿಗೆ ಮರಳಲು ಸಾಧ್ಯವೇ? ಇಲ್ಲ, ದೇಬು ಇನ್ನು ತನ್ನ ಬದುಕಿನಲ್ಲಿ ಎಂದೂ ಮೊದಲಿನಂತಾಗುವುದಿಲ್ಲ. ತಾನು ಹಿಮವಂತನೊಂದಿಗೆ ಹೋಗುತ್ತಿರುವುದು ಸರಿಯೇ? ದೇಬುವನ್ನು ಈ ಸ್ಥಿತಿಯಲ್ಲಿ ಬಿಟ್ಟು ಹೊರಟಿದ್ದು ಸರಿಯೇ? ಹಿಮವಂತನನ್ನು ಪ್ರೀತಿಸಲು ನನ್ನಿಂದ ಸಾಧ್ಯವೇ? ದೇಬುವನ್ನು ಮರೆಯಲು ಈ ಜನ್ಮದಲ್ಲಿ ಸಾಧ್ಯವೇ? ಇವೆಲ್ಲ ಪ್ರಶ್ನೆಗಳ ನಡುವೆ ಮೌನವಾಗಿ ಕುಳಿತಿದ್ದ ಪ್ರಾರ್ಥನಾಳ ಮನಸ್ಸು ಈಗ ಬರಿದಾಗಿತ್ತು. ಬದುಕಿನಲ್ಲಿ ಒಂದು ನಿರ್ಧಾರ ತೆಗೆದುಕೊಂಡ ಮೇಲೆ ಅದಕ್ಕೊಂದು ತಾರ್ಕಿಕ ಅಂತ್ಯ ಇರಬೇಕಲ್ಲವೇ? ಆಲೋಚಿಸುತ್ತಿದ್ದ ಪ್ರಾರ್ಥನಾಳಿಗೆ ಅದೇನೋ ತೀವ್ರವಾದ ಆಯಾಸ ಮತ್ತು ನಿದ್ರೆ ಬಂದಂತಾಯಿತು. ಅವಳು ಕಣ್ಣು ಮುಚ್ಚಿದಳು.
ಅವಳಿಗೆ ಎಚ್ಚರವಾದಾಗ ಕಾರು ನಿಂತಿತ್ತು. ಹಿಮವಂತ್ ಹಿಂದಿನ ಸೀಟಿನಿಂದ ತನ್ನ ಚಿತ್ರವಿಚಿತ್ರದ ಪುಟ್ಟ ಪುಟ್ಟ ಗಂಟುಗಳನ್ನು ಹೊರಕ್ಕೆ ತೆಗೆಯುತ್ತಿದ್ದ. ಗಾಢವಾದ ಕತ್ತಲೆಯಲ್ಲಿ ಮನೆಗಾಗಿ ಹುಡುಕಿದವಳಿಗೆ, ಮಧ್ಯರಾತ್ರಿಯ ಕತ್ತಲಿನಲ್ಲಿ ಕಾಣಿಸಿದ್ದು ಶಿವಮೂರ್ತಿ ಸರ್ಕಲ್ ಮತ್ತು ಶಾಂತಪ್ಪನವರ ಮನೆಯ ಕಂಪೌಂಡಿನಲ್ಲಿದ್ದ ಮಲ್ಲಿಗೆ ಬಳ್ಳಿ. "ಹಿಮೂ, ಇಲ್ಲಿಗೆ ಬಂದಿದ್ದೀವಾ?" ಅಂತ ಉದ್ಗರಿಸಿದಳು. ಹಿಮವಂತ್ ಸುಮ್ಮನೆ ಒಮ್ಮೆ ತನ್ನ ಗಂಟುಗಳ ಸಮೇತ ಶಾಂತಪ್ಪನವರ ಮನೆಯ ಪಕ್ಕದಿಂದ ನಡೆದು ಹೋಗಿ ಹಿತ್ತಿಲಿನಲ್ಲಿದ್ದ ಅದೇ ಹಳೆಯ ಔಟ್‌ಹೌಸಿನ ಮುಂದೆ ನಿಂತ. ರಾತ್ರಿಯ ಮೂರನೇ ಜಾವ ಆರಂಭವಾಗಿತ್ತು. ಅವತ್ತು ಚನ್ನರಾಯಪಟ್ಟಣದಿಂದ ನಡೆದುಬಂದು ಈ ಕೋಣೆ ತಲುಪಿದಾಗ ಆರಂಭವಾದಂಥದೇ ಮೂರನೇ ಜಾವ.
ಅಂಥ ಕತ್ತಲಲ್ಲೂ ಕಿಸೆಯಿಂದ ಬೀಗದ ಕೈ ತೆಗೆದು ಅವತ್ತಿನಂತೆಯೇ ಬೀಗದ ಕಣ್ಣಿಗೆ ಕರಾರುವಾಕ್ಕಾಗಿ ಚುಚ್ಚಿ ಬಾಗಿಲು ತೆಗೆದು ಕೋಣೆಯ ಸ್ವಿಚ್ಚು ಹಾಕಿದ. ಬಾಗಿಲಲ್ಲಿ ನಿಂತ ಪ್ರಾರ್ಥನಾ ಅದೇಕೋ ಥಟ್ಟನೆ ತನ್ನ ಬಲಗಾಲ ಹೆಬ್ಬೆರಳು ನೋಡಿಕೊಂಡಳು. ಅವತ್ತು ಹೆಬ್ಬೆರಳು ಸೀಳಿ ಗಾಯವಾಗಿತ್ತು. ಇವತ್ತು ಹೆಬ್ಬೆರಳಿಗೂ ಪಾದಕ್ಕೂ ನಿಶ್ಚಿತಾರ್ಥದ ಮೆಹಂದಿ.
"ಬಾ ಒಳಕ್ಕೆ ಪ್ರಾರ್ಥನಾ. ಇವತ್ತಿನಿಂದ, ಈ ಅಪರಾತ್ರಿಯ ನಿಮಿಷದಿಂದಲೇ ನಾವು ಹೊಸ ಬದುಕು ರೂಪಿಸಿಕೊಳ್ಳಬೇಕು. ಈ ಪುಟ್ಟ ಕೋಣೆಯಿಂದಲೇ." ಅಂದವನೇ ಕೋಣೆಯಲ್ಲಿ ಜಮೆಯಾಗಿದ್ದ ಧೂಳನ್ನು ಸಣ್ಣಗೆ ಒರೆಸತೊಡಗಿದ. ಮೊಟ್ಟಮೊದಲ ಬಾರಿಗೆ ಈ ಕೋಣೆಗೆ ಬಂದಾಗ ಎಡಗಾಲಿಟ್ಟು ಒಳಕ್ಕೆ ಬಂದಿದ್ದೆ ಅಂತ ನೆನಪಾಯಿತು ಪ್ರಾರ್ಥನಾಳಿಗೆ. ಅವತ್ತು ಶಕುನ ಸರಿಯಾಗಿರಲಿಲ್ಲ, ಇವತ್ತು?
ಎರಡೇ ನಿಮಿಷದಲ್ಲಿ ರೂಮು ಚೊಕ್ಕಟಗೊಳಿಸಿ ಮಧ್ಯದಲ್ಲೊಂದು ಚಾಪೆಹಾಕಿ ಅವಳಿಗೆ ಬಟ್ಟೆ ಬದಲಿಸಿಕೊಳ್ಳಲು ಅವಕಾಶವಾಗಲೆಂಬಂತೆ, ತಾನು ಪದ್ಮಾಸನ ಹಾಕಿ ಕಣ್ಣು ಮುಚ್ಚಿಕೊಂಡು ಧ್ಯಾನಕ್ಕೆ ಕುಳಿತ."""
}

ENGLISH_FIXES = {
    2: """Heli Hogu Karana (A Novel)
Ravi Belagere

Bhavana Prakashana
#2, 80 Feet Road, Banashankari 2nd Stage, Padmanabhanagar, Bengaluru - 560 070
Email: bhavanaprakashana@gmail.com
Website: www.ravibelagere.com
Phone: 94480 51726""",

    3: """Heli Hogu Karana (A Novel)
Ravi Belagere
Pages: 339
Price: Rs. 350
Copies: 3000
Printed at: Sri Ganesh Printers Pvt. Ltd., Bengaluru.

Printing History:
First Edition: September 2003
Second Edition: November 2008
Third Edition: April 2009
Fourth Edition: December 2009
Fifth Edition: October 2010
Sixth Edition: December 2011
Seventh Edition: April 2012
Eighth Edition: February 2013
Ninth Edition: June 2014
Tenth Edition: January 2015
Eleventh Edition: January 2016
Twelfth Edition: August 2016
Thirteenth Edition: June 2017
Fourteenth Edition: August 2018
Fifteenth Edition: July 2019
Sixteenth Edition: December 2019
Seventeenth Edition: August 2020
Eighteenth Edition: January 2021
Nineteenth Edition: August 2021
Twentieth Edition: January 2022
Twenty-First Edition: July 2022
Twenty-Second Edition: January 2023
Twenty-Third Edition: June 2023
Twenty-Fourth Edition: August 2023
Twenty-Fifth Edition: December 2023
Twenty-Sixth Edition: March 2024
Twenty-Seventh Edition: June 2024
Twenty-Eighth Edition: August 2024
Twenty-Ninth Edition: November 2024
Thirtieth Edition: January 2025
Thirty-First Edition: April 2025""",

    7: """If she had not walked with him, she would have got lost somewhere along the way, she thought. Her ankle, which she had twisted near Tarikere, had started to pain and must be bleeding. She dragged her feet with effort. Himavant looked at her affectionately and tightened his grip in his pocket. The cold was beginning to numb their fingers. "Who are you?" a hoarse voice called out, making them both startle. The voice came unexpectedly from the darkness in the northeastern corner of Shivamurthy Circle. Behind it emerged a night-patrol police constable wearing a heavy coat. His heavy boots clicked on the ground. Under the street light, his stubbled face looked even harsher. "Who are you?" he asked again, coming closer. A bidi burned angrily between his fingers. For some reason, he suddenly reminded her of her father! "I am Himavant, her name is Prarthana," Himavant answered in a calm voice. "Where are you coming from?" the constable asked. "From Channarayapatna." "At what time? Which bus? Where is the ticket?" The questions came firing from the constable's mouth. "We didn't come by bus, we walked. Where would we get a ticket? We need to go home," Himavant replied fluently. The constable's stubbled face was filled with surprise. Walking from Channarayapatna? Are they crazy? "You should at least lie convincingly. Come to the station. You seem to have brought a girl along, who knows if there's a missing case registered. The inspector isn't nice. You know how sub-inspectors are? Very strict." "I will tell you once more. My name is Himavant, she is Prarthana. We are both over eighteen. If you call, we will come anywhere in the morning. Past the circle, it's a five-minute walk. I live in the backyard of merchant Shantayya's house. We didn't walk because we didn't have bus fare. I have one hundred and twenty rupees in my pocket." Himavant was about to say something else. "Then why did you walk?" the constable interrupted. "We want to walk together for the rest of our lives, at least till Shivamogga, to see if we could do it through grit. There are only five kilometers left...""",

    11: """She sat in silence for a while. "Himavant!" she called out, her eyes filled with a sudden vulnerability. That night too was like hell. The town lights had gone out. Lord! He must have applied some medicine to her forehead. The clothes she wore must have given her a new look, Lord! What shame taught was the smile of a gentle surprise. A sort of confidence flickered in her eyes. In grown-up girls, this innocence is dead. The look on the faces of beautiful but unintelligent women is not innocence; only in a face where a playful confidence and innocence mix does it look beautiful. Perhaps that was what was meant. Even as one thinks so, her consent is obtained.
Thus, starting from Channarayapatna, the two unclear shadows walked and entered the small room in the backyard of merchant Shantappa’s house near Shivamurthy Circle that night, unnoticed by anyone, except for Rasool Jamadar. He had quietly walked behind them, stood at the door to confirm that both had reached their room, and then returned.
For those shadows, there was no other shelter in the whole world. One shadow was struggling in helplessness, while the other held its hand in consent.
"Will you really give me a life, Himavant?" Prarthana had asked during their first meetings.
"I don't know. But I can give you everything life has given me, without any deceit. In return, I will not ask what you will give me, because life is not something to be given or taken. It is something to be built. Let the hell you walked out of in your house end there. I will be waiting for you at the Channarayapatna bus stand. There might be a thousand buses and ten roads to reach Shivamogga, but remember: we must walk. We must walk on the main road itself. Dream whatever dream you want, Prarthana, until we reach Shivamogga from Channarayapatna. From the moment you step inside the threshold of my house in Shivamogga...""",

    64: """"If you identify the boys who did this, let's file a complaint and then you can go," Rasool Jamadar told Himavant in a soft, respectful voice, holding Shantappa's hand as they walked out of the hospital. "Can't we file it in the morning? Let him sleep for a while now," Shantappa suggested. Not knowing whose advice to follow, Himavant stood silent for a moment. Then, suddenly releasing Shantappa's hand, he grabbed Jamadar's arm and led him to another corner of the hospital yard where it was dark. Himavant's expression changed. Sweat began to bead on his bandaged forehead. He licked his lips twice. Then, clearing his throat softly, he said, "What will you do with a complaint, Sab? Wake up at dawn and go to Gonigara Keri. Gather Virupaksha, Venkatesha, Naga from the last house, and his uncle's son Ganesha. Bring them all. I will come in the morning to see them. Go home now, your daughter's husband will have returned. Don't start arguing, eat a couple of bites and sleep. Get up at dawn and do what I said. Go." Within three seconds of saying this, Himavant's face relaxed, and his eyes cleared. Rasool Jamadar stood stunned, not knowing what to do. Having said his piece, Himavant walked back to Shantappa's scooter without another word. Jamadar stood there like a stone statue until the two of them disappeared from the hospital premises, sweating all over for some reason. But a bigger surprise was waiting for him at home. Before he even knocked on the door, he heard his daughter's husband talking inside the house. The entire house was filled with joy; the son-in-law who had left in anger had returned! Were the words of that strange boy starting to come true? Rasool Jamadar's shock was not going to end soon. At that moment, Jamadar did not realize that he would spend many of the remaining years of his life living alongside this mystery. Meanwhile, Himavant, without saying much, went to his backyard room at Shantappa's house and lay flat on the mat without a pillow. Deep in his brain, blood seemed to surge suddenly, numbing his head. In her room, Prarthana woke up screaming from a nightmare.""",

    78: """Deb, who was preparing for the third round after finishing two pints, was also thinking about the same thing that night. Sitting opposite him, Urmi was enjoying her cigarette more than the whiskey. The night was as deep as sorrow in the forest. By the time their car reached the forest lodge, the cook, who had been waiting for them, placed the food on the dining table, instructed them to close the door when they left, and went away. Now, they were the only two in the entire forest! The friendship that had started in the college corridors, matured in the dim lights of Bathi dhabas near Davanagere, had now walked into the middle of the Shivamogga forest. Urmi was not so foolish as to not understand the plea in his eyes, nor was she so unwise as to reject someone like him. An only son with huge property, handsome, smart, and above all: "I love you more than I have loved any other girl. True, we wandered together, but all that was pure playfulness. From today until my last day, it's only you. What do you say?" Deb asked clearly amidst the dense silence of the forest lodge. Though his voice, fueled by two pints of whiskey, carried a hope of winning, there was a tense chord of anxiety that a single rejection from Urmi would crush him. "Don't joke, Deb. I know you flirt very well. Hearing words like 'body, speech, mind' from you sounds like a joke. I still have to become a doctor. If I get nothing else, I will specialize in Forensics and become the most famous doctor who performs autopsies in India. After achieving all that, I will throw my medical books in the drain and read all the history books in the libraries of India. I want to travel around forts searching for the footprints of kings. I want to smoke cigarettes and drink until I fall to the ground. If I become your wife before all this, my life will feel incomplete. By the way, whenever I get some free time, you know Kasuri Kaveramma in Davanagere? I want to live in her house like a pure prostitute for four days. And you say you love someone like me, Deb? You must be crazy. Ask me directly, 'shall we flirt?' It sounds healthy. What do you say?""",

    129: """Deb had a strange resentment towards Himavant. "How can a girl like you worship him so much? I cannot tolerate it. It might be your devotion. Or maybe it has been your habit from the start. Or is it respect because he paid for your education? But no man in this world deserves such respect. I cannot stand to see that bow!" Deb had said after coming home. Later, when Himavant himself got up, heated water for her bath, poured castor oil on his hands and gently pressed it onto her scalp, Prarthana suddenly realized that she hadn't bowed to his feet in respect as soon as they met this time. A wave of anxiety washed over her. Should she just ask? Should she fall at Himu's feet, shed tears, press her forehead to the ground and say, "I made a mistake Himu, please forgive me. I will never even look towards Debu again in my life. My Himavant, let me dissolve into your generosity, your natural love, your ocean-like personality just like before. I am sorry! I have no life without you. There is no other man for me in this world." Should she say that? But the words wouldn't come out. As he gently pressed the cool oil onto her curly hair as she sat on a small stool, Himavant asked in an affectionate tone, "Didn't you miss me at all when you went to the new place?" Prarthana felt as if she had dropped into the lap of a giant eye. "It wasn't like that. In the beginning, I struggled to adjust to the new atmosphere there. The college was new, the hostel was new. In fact, I felt that if I stepped on the ground, my feet would wear out. Gradually, I adjusted. Yet, for every little thing, I would remember you and feel like crying. Once classes started, it reduced a bit. I met Urmi Didi. And then there were those little letters we wrote in college, and the letters you sent now and then. When we read them, it felt like you were right in front of us, as if we had never been far from each other. That doesn't mean I didn't remember you...""",

    140: """He could have left. He could have got off the bus on the way. What was the need to tell him that he was close, that he was coming from Davanagere? Aren't these small deceptions the cause of the ultimate shock? Determined to resolve this suspicion once and for all, he began to twist the accelerator of his motorcycle. Like a wild horse, the bike sped on. As Himavant's mind grew agitated again, he crossed Honnali, then Malebennur, and was about to turn towards Harihar when he suddenly hit the brakes. Parked outside a small roadside dhaba-like hotel, he saw Debashish Bandopadhyay's car. There was no one inside the car; they must be sitting inside the hotel. From a distance, he turned off the key, stopping the engine's roar. Without making a sound, he parked the bike in front of the hotel and, in just two steps, walked into the small thatched-roof hotel. That was when he saw Debu! Debashish Chandra Nath Bandopadhyay. "Debu, park the car here. I will get into the bus. I will meet you in the evening near the hostel. I will go from Malebennur to Davanagere by bus," Prarthana had said as she got down from the car, just fifteen minutes before Himavant walked into the dhaba. A woman's mind, determined to deceive, can anticipate danger. From the moment she left Shivamogga, she had been anxious. The bus was empty. As Himavant stood by the window with his innocent eyes, telling her to study well, write letters, and ask for money if needed, her eyes were searching for Debu's car. Deceiving Himavant while far away in Davanagere was one thing; but searching for Debu while keeping Himavant right in front of her was like deceiving God himself. But a woman's desires can drive her to any deception. Had she not shaken off Himavant, who was sleeping with his head on her arm enjoying their closeness, and run to call Debu? Had she not told lie after lie to Himavant since coming to Shivamogga?""",

    191: """If she could take her body and go with someone in the middle of the night like that—what is the meaning of the word 'love'? What is the meaning of freedom? What is the meaning of Prarthana's honesty, her devotion, her faith, her goodness? If she was truly good and honest, why did she leave Himavant, who loved her so deeply, and come to me? And after coming to me, why did she as easily go with Sujay in the middle of the night on the dark road of Harihar? Prarthana is not honest! She also has different faces, and innocence is just one of them, which can change at any time. I boasted that I won this innocent girl, that I snatched her from Himavant and triumphed. I thought I won a girl like her. But the one who got ruined was me! I got defeated in front of an ordinary guy like Sujay. Prarthana might give excuses for this: 'Because you wandered on the Harihar road with Urmi, I also sat on your roommate Sujay's bike, hugging him. Let's end it there. My true love is only for you, Debu Babu. Forget what happened.' But does the mind forget? A man might be a great adulterer, he might bring an adulterous woman to satisfy his afternoon lust, but as long as they are together, he expects even that adulterous woman to look nowhere else and be loyal to him alone. In such a case, can I ever forget the brown wounds on Prarthana's body? After all that, will I be able to marry her and be happy? What has Prarthana done! She has shattered the most delicate dream of my life. He sat staring at the wall with empty eyes. "Get up, Huzoor. Go take a bath quickly. You didn't even eat dinner last night. Your stomach must be burning. Let's go out, just the two of us, eat something, and spend an excellent afternoon together. Today I will sing all the songs I kept for you... Only for you," Prarthana pulled him up by his arm. As Debu was bathing, she stood in front of the full-length mirror, combing her tangled hair. She felt the drops flying from her hair falling onto a sheet of paper on the table in front of the mirror. Thinking it might be some important paper that would get wet, she quickly picked it up.""",

    338: """Heli Hogu Karana / 338
She touched the feet of Debu's father and mother in respect. When Debu's father mechanically patted her head and stroked her back with affection, she could not hold back her grief and burst into deep sobs. But suppressing her rising tears, when she approached Debu, who sat on the sofa looking stunned, her mind became as still as a lake, and the volcano of all her emotions suddenly went cold. "Good bye Debu..." she said, placing a gentle kiss on his forehead, and unable to stand there any longer, she started walking towards the portico.
As she was crossing the veranda, Debu tried to make a sound to say something. Fearing that hearing his faint voice just once more would shatter her heart, she quickly stepped towards Urmi, who was standing on the veranda, and said, "Let's go, Didi, let's go!"
"No, he wants you alone in the car. He has instructed that none of us should accompany you, Himu. You go, we will come in another car. Me, Jamadar, and Debu!" Urmi said.
A storm raged in Prarthana's eyes. Where is Debu coming? Why is he coming? Oh Lord, what else is bound to happen? Prarthana asked out loud.
"It will take weeks for Debu to fully recover. A doctor must always be with him. If not a doctor, at least an attendant. You are leaving out of necessity. Debu's parents cannot look after him in this state. I know a doctor in Shivamogga who runs a nursing home. I don't feel like taking him to Davanagere College in this condition. People shouldn't see Debu, who was so handsome, in this state. It seems I have got used to all this. You leave someone behind, and I end up deciding to attend to them. Why does it happen this way? I don't understand why life repeatedly brings both of us to such crossroads. You go, I will convince his parents, take him and come to Shivamogga in a taxi. I will try to meet you..." Urmi spoke in a pained voice. All of Prarthana's questions, curiosity, and anxieties died in a single stroke, and it felt as though she was returning to that same familiar life in Shivamogga with Himavant.""",

    341: """Heli Hogu Karana / 341
Why did she agree to go and see him before leaving? Having seen him like that for the last time, is it possible for her to return to life now? No, Debu would never be the same again in her life. Was it right for her to go with Himavant? Was it right to leave Debu in this condition? Was it possible for her to love Himavant? Was it possible to forget Debu in this lifetime? Sitting in silence amidst all these questions, Prarthana's mind was now empty. Once a decision is made in life, shouldn't there be a logical end to it? Thinking about it, she felt a profound exhaustion and drowsiness. She closed her eyes.
When she woke up, the car had stopped. Himavant was taking out his small, strange bundles from the back seat. To her, who had been looking for a house in the deep darkness, what appeared in the midnight gloom was Shivamurthy Circle and the jasmine vine in the compound of Shantappa's house. "Himu, have we arrived here?" she exclaimed. Without a word, carrying his bundles, Himavant walked past Shantappa's house and stood in front of the same old outhouse in the backyard. The third watch of the night had begun—the same third watch that had begun when they had walked from Channarayapatna and reached this room.
Even in that darkness, he took out the key from his pocket, inserted it precisely into the keyhole just like that day, opened the door, and switched on the room's light. Standing at the door, Prarthana suddenly looked down at the big toe of her right foot. That day, the toe had been split and injured. Today, her toe and foot bore the henna of engagement.
"Come inside, Prarthana. From today, from this midnight minute itself, we must build a new life. From this tiny room." Saying this, he began to gently wipe away the dust accumulated in the room. Prarthana remembered that when she had first come to this room, she had stepped in with her left foot. The omen was not right that day; what about today?
Within two minutes, he cleaned up the room, spread a mat in the middle to give her space to change, and sat down in the lotus position with his eyes closed to meditate."""
}

def main():
    print("Writing corrected page files...")
    
    # 1. Write Kannada files
    for p_num, content in KANNADA_FIXES.items():
        fname = f"page_{p_num:04d}.txt"
        path = os.path.join(KANNADA_DIR, fname)
        print(f"  Writing {path}...")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())
            
    # 2. Write English files
    for p_num, content in ENGLISH_FIXES.items():
        fname = f"page_{p_num:04d}.txt"
        path = os.path.join(ENGLISH_DIR, fname)
        print(f"  Writing {path}...")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())
            
    print("Done writing fixes!")

if __name__ == "__main__":
    main()
