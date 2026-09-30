import type { Configuration } from 'webpack';
import { rules } from './webpack.rules';
import { plugins } from './webpack.plugins';
export const rendererConfig: Configuration = {
  devtool: 'source-map',
  module: {
    rules: [...rules, { test: /\.css$/, use: ['style-loader', 'css-loader'] }],
  },
  plugins,
  resolve: { extensions: ['.js', '.ts', '.jsx', '.tsx', '.css'] },
};
