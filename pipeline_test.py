from analysis.pipeline import generate_report

paths = [
    'static/uploads/007a12ce7ecd4df4bac8d63c747f9664_WIN_20260713_16_20_24_Pro.jpg',
    'static/uploads/03ad97cf795441b7bc77fa50bcaab33d_blank.jpg',
    'static/uploads/042f02fcb71b4d3e8b35266b45b0b784_lena2.jpg',
]

print('Testing generate_report on sample images...')
report = generate_report(paths)
print(report)
